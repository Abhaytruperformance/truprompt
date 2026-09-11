from pydantic import BaseModel, Field

from app.core.config import settings


def share_to_dict(row: dict) -> dict:
    return {
        "_id": row["id"],
        "orgId": row["org_id"],
        "promptId": row["prompt_id"],
        "token": row["token"],
        "hasPassword": bool(row.get("password_hash")),
        "createdAt": row["created_at"],
        "revokedAt": row.get("revoked_at"),
        "generationLimit": row.get("generation_limit"),
        "generationCount": row.get("generation_count", 0),
    }


class ShareCreate(BaseModel):
    password: str | None = None
    # Unlimited anonymous LLM spend must be something an admin chooses, not
    # what happens when they leave a field blank -- defaults to a safe cap;
    # an explicit `null` (not just omitting the field) is required to opt
    # into no limit at all.
    generationLimit: int | None = Field(
        default=settings.DEFAULT_SHARE_GENERATION_LIMIT, ge=1, le=settings.MAX_SHARE_GENERATION_LIMIT
    )
