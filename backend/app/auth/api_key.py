import hashlib
import math
import random
import threading
import time
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.db.pg import org_scoped_cursor
from app.db.supabase import supabase


def hash_key(plaintext_key: str) -> str:
    return hashlib.sha256(plaintext_key.encode()).hexdigest()


class ApiKeyScope(str, Enum):
    """The two capability tiers that exist on the public API + MCP surface
    today. A str Enum (not plain constants) so Pydantic validation, OpenAPI
    schema generation, and every call site all stay in sync off one
    definition. Add a third tier only when a genuinely distinct capability
    (e.g. analytics:read) actually ships -- don't pre-fragment a 6-endpoint
    surface.

    READ -- list_prompts, get_prompt, list_tags, list_departments (MCP).
    Browsing only, no LLM cost. Named "library:" rather than "prompts:"
    deliberately -- tags/departments are metadata about the library, not the
    prompts resource itself.

    GENERATE -- generate_prompt (MCP) and POST /v1/prompts/{id}/generate
    (REST). The one action that costs money and can be abused if a key
    leaks.

    Security invariant: GENERATE does NOT imply READ, and that's deliberate,
    not an oversight -- generate_prompt reads the stored prompt via its own
    internal org_scoped_cursor query and never returns that stored content to
    the caller (only the freshly generated optimizer/prompt text comes
    back). Any endpoint or tool guarded only by GENERATE must never expose
    stored prompt content or library metadata beyond what's required to
    generate -- the moment one does, it needs READ too. This is what
    protects the independence decision from a future refactor accidentally
    reintroducing a read path under the generate scope.
    """

    READ = "library:read"
    GENERATE = "prompts:generate"


class InvalidApiKey(Exception):
    """Raised by resolve_api_key_org when the key is missing/invalid/revoked."""


class InsufficientScope(Exception):
    """Raised by resolve_api_key_org when the key doesn't carry a scope a
    caller requires. Sibling to InvalidApiKey/RateLimitExceeded, not a
    subclass -- different failure, same reasoning: each transport's existing
    except-block for the other two shouldn't accidentally swallow this too."""

    def __init__(self, scope: "ApiKeyScope"):
        self.scope = scope
        super().__init__(f"Missing required scope: {scope.value}")


class RateLimitExceeded(Exception):
    """Raised by resolve_api_key_org when a key has exceeded its request
    budget for the current window. Deliberately NOT a subclass of
    InvalidApiKey -- these are different failures, and keeping them separate
    means each transport's existing except-block for InvalidApiKey doesn't
    accidentally swallow a rate-limit rejection too."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry after {retry_after}s")


# ponytail: in-process fixed-window counter -- thread-safe (the Lock below),
# but NOT process-safe: resets on restart and doesn't share state across
# workers if this ever runs as more than one uvicorn process. Move to Redis
# INCR/EXPIRE then, without changing resolve_api_key_org's callers.
_rate_limit_state: dict[str, tuple[float, int]] = {}
_rate_limit_lock = threading.Lock()


def _check_rate_limit(key_id: str) -> None:
    window_seconds = settings.API_KEY_RATE_LIMIT_WINDOW_SECONDS
    limit = settings.API_KEY_RATE_LIMIT_PER_MINUTE
    now = time.monotonic()

    with _rate_limit_lock:
        # Occasional sweep of fully-expired entries so a long-running process
        # that sees many distinct keys over time doesn't grow this dict
        # forever -- cheap (1-in-200 calls), no background thread needed.
        if random.randint(1, 200) == 1:
            expired = [
                k for k, (window_start, _) in _rate_limit_state.items()
                if now - window_start >= window_seconds
            ]
            for k in expired:
                del _rate_limit_state[k]

        window_start, count = _rate_limit_state.get(key_id, (now, 0))
        if now - window_start >= window_seconds:
            window_start, count = now, 0

        count += 1
        _rate_limit_state[key_id] = (window_start, count)

        if count > limit:
            retry_after = math.ceil(window_seconds - (now - window_start))
            raise RateLimitExceeded(retry_after=max(retry_after, 1))


def resolve_api_key_org(plaintext_key: str | None, required_scope: ApiKeyScope | None = None) -> str:
    """Resolves an org_id from a plaintext API key, shared by both the REST
    dependency below and the MCP server's own auth middleware (app/mcp_server.py) --
    one auth implementation, two transports.

    The lookup itself has to run on the service-role client, not
    org_scoped_cursor -- the org isn't known yet at this point (the presented
    hash could belong to any org), same precedent as the Sharing/
    accept_invitation token lookups elsewhere in this codebase.

    required_scope: None skips the scope check entirely (used for auth-only
    resolution). scopes=NULL on the row (a legacy key, created before scopes
    existed) always passes -- see ApiKeyScope's docstring for the migration
    note on eventually eliminating that. scopes=[] passes nothing.
    """
    if not plaintext_key:
        raise InvalidApiKey("Missing API key")

    key_hash = hash_key(plaintext_key)

    result = (
        supabase.table("api_keys")
        .select("*")
        .eq("key_hash", key_hash)
        .is_("revoked_at", "null")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise InvalidApiKey("Invalid or revoked API key")

    key_row = rows[0]
    org_id = key_row["org_id"]

    # An expired key must fail exactly like a revoked one -- adding the
    # column without enforcing it here would make it purely cosmetic.
    expires_at = key_row.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
        raise InvalidApiKey("API key has expired")

    if required_scope is not None:
        scopes = key_row.get("scopes")
        if scopes is not None and required_scope.value not in scopes:
            raise InsufficientScope(required_scope)

    # Checked before last_used_at is touched -- a rejected/throttled request
    # must not update it, or "last used" starts looking active when the key
    # was actually being blocked.
    _check_rate_limit(key_row["id"])

    # A normal org-scoped write from here on -- the org is now known.
    with org_scoped_cursor(org_id) as cur:
        cur.execute("update api_keys set last_used_at = now() where id = %s", (key_row["id"],))

    return org_id


def get_api_key_org(request: Request, required_scope: ApiKeyScope | None = None) -> str:
    """Resolves the calling org_id from an `Authorization: Bearer <key>` header."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    plaintext_key = auth_header[len("Bearer ") :].strip()
    try:
        return resolve_api_key_org(plaintext_key, required_scope)
    except InvalidApiKey as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except InsufficientScope as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded, please slow down",
            headers={"Retry-After": str(exc.retry_after)},
        )


def require_api_key_scope(scope: ApiKeyScope):
    """Dependency factory for REST routes that need a specific scope, mirroring
    app/auth/dependencies.py's require_role(minimum) shape. Any future REST
    read endpoint (e.g. a GET /v1/prompts, if one ships) should use
    Depends(require_api_key_scope(ApiKeyScope.READ)) the same way."""

    def _check(request: Request) -> str:
        return get_api_key_org(request, required_scope=scope)

    return _check
