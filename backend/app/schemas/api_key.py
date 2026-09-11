from pydantic import BaseModel, Field

from app.auth.api_key import ApiKeyScope


def _scopes_label(scopes: list[str] | None) -> str:
    if scopes is None:
        return "All (legacy)"
    has_read = ApiKeyScope.READ.value in scopes
    has_generate = ApiKeyScope.GENERATE.value in scopes
    if has_read and has_generate:
        return "Read + Generate"
    if has_read:
        return "Read only"
    if has_generate:
        return "Generate only"
    return "No permissions"


def api_key_to_dict(row: dict) -> dict:
    scopes = row.get("scopes")
    return {
        "_id": row["id"],
        "orgId": row["org_id"],
        "name": row["name"],
        "keyPrefix": row["key_prefix"],
        "createdAt": row["created_at"],
        "lastUsedAt": row.get("last_used_at"),
        "expiresAt": row.get("expires_at"),
        "scopes": scopes,
        "scopesLabel": _scopes_label(scopes),
    }


class ApiKeyCreate(BaseModel):
    name: str
    # None = no expiry (backward compatible with every key created before
    # this existed). Bounded so "expiring" can't mean "in 1000 years."
    expiresInDays: int | None = Field(default=None, ge=1, le=3650)
    # None = full-access default (both scopes) -- matches today's de facto
    # "keys can do everything" behavior unless an admin deliberately narrows
    # it. Never written as NULL on the row itself -- see create_api_key.
    scopes: list[ApiKeyScope] | None = None
