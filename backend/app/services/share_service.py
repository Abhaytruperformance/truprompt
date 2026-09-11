import hashlib
import random
import secrets
import threading
import time

from app.db.pg import org_scoped_cursor
from app.db.supabase import supabase

# Share-link passwords are a low-stakes secondary gate on a read-only view,
# not an account credential -- stdlib PBKDF2 is proportionate, no need for
# bcrypt/passlib (neither is installed).
_PBKDF2_ITERATIONS = 260_000

# ponytail: in-process, per-token failed-attempt counter -- same tradeoff as
# the API-key rate limiter (resets on restart, not shared across workers).
# Bounds password brute-forcing against a public, unauthenticated endpoint.
_FAILED_ATTEMPT_LIMIT = 10
_FAILED_ATTEMPT_WINDOW_SECONDS = 300
_failed_attempts: dict[str, tuple[float, int]] = {}
_failed_attempts_lock = threading.Lock()


class TooManyAttempts(Exception):
    pass


def _check_and_record_failure(token: str) -> None:
    now = time.monotonic()
    with _failed_attempts_lock:
        if random.randint(1, 200) == 1:
            expired = [
                k for k, (window_start, _) in _failed_attempts.items()
                if now - window_start >= _FAILED_ATTEMPT_WINDOW_SECONDS
            ]
            for k in expired:
                del _failed_attempts[k]

        window_start, count = _failed_attempts.get(token, (now, 0))
        if now - window_start >= _FAILED_ATTEMPT_WINDOW_SECONDS:
            window_start, count = now, 0
        count += 1
        _failed_attempts[token] = (window_start, count)
        if count > _FAILED_ATTEMPT_LIMIT:
            raise TooManyAttempts("Too many incorrect attempts, try again later")


def _clear_failures(token: str) -> None:
    with _failed_attempts_lock:
        _failed_attempts.pop(token, None)


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS)
    return secrets.compare_digest(digest.hex(), password_hash)


def create_share(
    org_id: str, prompt_id: str, created_by: str, password: str | None, generation_limit: int | None = None
) -> dict:
    token = secrets.token_urlsafe(24)
    password_hash = password_salt = None
    if password:
        password_hash, password_salt = hash_password(password)

    with org_scoped_cursor(org_id, created_by) as cur:
        cur.execute(
            """insert into prompt_shares
               (org_id, prompt_id, token, password_hash, password_salt, created_by, generation_limit)
               values (%s, %s, %s, %s, %s, %s, %s) returning *""",
            (org_id, prompt_id, token, password_hash, password_salt, created_by, generation_limit),
        )
        return cur.fetchone()


def list_shares(org_id: str, prompt_id: str) -> list[dict]:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "select * from prompt_shares where prompt_id = %s and revoked_at is null",
            (prompt_id,),
        )
        return cur.fetchall()


def revoke_share(org_id: str, share_id: str) -> dict | None:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "update prompt_shares set revoked_at = now() where id = %s and org_id = %s returning *",
            (share_id, org_id),
        )
        return cur.fetchone()


def get_share_by_token_public(token: str) -> dict | None:
    # Unauthenticated by design: possessing the random unguessable token is
    # itself the authorization for this lookup -- same precedent already
    # established by org_service.accept_invitation's token lookup. The org_id
    # isn't known yet, so this can't go through org_scoped_cursor.
    result = (
        supabase.table("prompt_shares")
        .select("*")
        .eq("token", token)
        .is_("revoked_at", "null")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def get_prompt_public(prompt_id: str) -> dict | None:
    result = supabase.table("prompts").select("*").eq("id", prompt_id).limit(1).execute()
    rows = result.data or []
    return rows[0] if rows else None


def current_version_number_public(prompt_id: str) -> int:
    """Same meaning as version_service.current_version_number (one past the
    last snapshot) but via the service-role client -- this runs in the
    pre-auth public-share path, same precedent as get_prompt_public itself,
    no org context/org_scoped_cursor available yet at this point."""
    result = (
        supabase.table("prompt_versions")
        .select("version_number")
        .eq("prompt_id", prompt_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return (rows[0]["version_number"] + 1) if rows else 1


class ShareNotFound(Exception):
    pass


class SharePasswordError(Exception):
    pass


def unlock_share(token: str, password: str | None) -> dict:
    """Looks up a share by token and verifies its password gate (if any).
    Shared by both public_shares.py routes so viewing a share and generating
    from it enforce the exact same rules."""
    share = get_share_by_token_public(token)
    if not share:
        raise ShareNotFound("Share not found")
    if share.get("password_hash"):
        if not password:
            raise SharePasswordError("Password required")
        # Checked before verifying, not after -- a locked-out token can't be
        # used to keep trying passwords one request at a time.
        _check_and_record_failure(token)
        if not verify_password(password, share["password_hash"], share["password_salt"]):
            raise SharePasswordError("Incorrect password")
        _clear_failures(token)
    return share


def try_increment_generation_count(share_id: str) -> bool:
    """Atomically increments generation_count if under generation_limit (or
    unlimited). Returns False if the limit has been reached. The service-role
    REST client has no server-side `column + 1` expression, so this uses a
    compare-and-swap retry instead of a naive read-then-write, which would
    otherwise have a real race between two concurrent requests both reading
    the same count and both proceeding."""
    for _ in range(5):
        result = (
            supabase.table("prompt_shares")
            .select("generation_count,generation_limit")
            .eq("id", share_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return False
        current = rows[0]["generation_count"]
        limit = rows[0]["generation_limit"]
        if limit is not None and current >= limit:
            return False

        update_result = (
            supabase.table("prompt_shares")
            .update({"generation_count": current + 1})
            .eq("id", share_id)
            .eq("generation_count", current)
            .execute()
        )
        if update_result.data:
            return True
        # else: another request changed the count between our read and write -- retry


def release_generation_count(share_id: str) -> None:
    """Releases a reservation try_increment_generation_count made when the
    LLM call it was reserved for actually failed -- otherwise "generation
    limit" would mean "generation attempts," not "successful generations,"
    and a visitor who got nothing back would still have consumed their
    quota. Same CAS retry shape as the increment, best-effort: if it can't
    land after a few retries under contention, a slightly generous limit is
    a far smaller problem than raising out of an already-failed request's
    exception handler."""
    for _ in range(5):
        result = (
            supabase.table("prompt_shares")
            .select("generation_count")
            .eq("id", share_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return
        current = rows[0]["generation_count"]
        if current <= 0:
            return
        update_result = (
            supabase.table("prompt_shares")
            .update({"generation_count": current - 1})
            .eq("id", share_id)
            .eq("generation_count", current)
            .execute()
        )
        if update_result.data:
            return
        # else: another request changed the count between our read and write -- retry

    # ponytail: gives up after 5 retries under heavy contention on one share
    # link, failing closed ("limit reached") rather than looping forever --
    # fine at this feature's realistic traffic (one public link, not a
    # high-throughput endpoint).
    return False
