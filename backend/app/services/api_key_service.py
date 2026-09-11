import secrets
from datetime import datetime, timedelta, timezone

from app.auth.api_key import ApiKeyScope, hash_key
from app.db.pg import org_scoped_cursor

KEY_PREFIX = "tp_"


def create_api_key(
    org_id: str,
    name: str,
    created_by: str,
    expires_in_days: int | None = None,
    scopes: list[ApiKeyScope] | None = None,
) -> tuple[dict, str]:
    """Returns (row, plaintext_key) -- the plaintext is never stored, only
    shown once at creation time (standard API-key UX, same as Stripe/GitHub).

    Always writes an explicit scopes array, never NULL -- NULL is a closed
    set reserved for keys that already existed before scopes shipped; no
    code path may reintroduce it going forward. scopes=None here means "use
    the full-access default" (both scopes), not "leave unrestricted" --
    callers that want a narrower key pass an explicit list."""
    plaintext_key = KEY_PREFIX + secrets.token_urlsafe(24)
    key_hash = hash_key(plaintext_key)
    key_prefix = plaintext_key[:12]
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=expires_in_days) if expires_in_days else None
    )
    scope_values = [s.value for s in (scopes if scopes is not None else list(ApiKeyScope))]

    with org_scoped_cursor(org_id, created_by) as cur:
        cur.execute(
            """insert into api_keys (org_id, name, key_hash, key_prefix, created_by, expires_at, scopes)
               values (%s, %s, %s, %s, %s, %s, %s) returning *""",
            (org_id, name, key_hash, key_prefix, created_by, expires_at, scope_values),
        )
        return cur.fetchone(), plaintext_key


def list_api_keys(org_id: str) -> list[dict]:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "select * from api_keys where org_id = %s and revoked_at is null order by created_at desc",
            (org_id,),
        )
        return cur.fetchall()


def revoke_api_key(org_id: str, key_id: str) -> dict | None:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "update api_keys set revoked_at = now() where id = %s and org_id = %s returning *",
            (key_id, org_id),
        )
        return cur.fetchone()
