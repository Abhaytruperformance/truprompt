from typing import Literal

from pydantic import BaseModel, Field, field_validator


def prompt_to_dict(
    row: dict, custom_fields: dict | None = None, tags: list | None = None, rating: dict | None = None
) -> dict:
    """Maps a Supabase `prompts` row to the camelCase shape the frontend expects."""
    rating = rating or {}
    return {
        "_id": row["id"],
        "orgId": row["org_id"],
        "userId": row["user_id"],
        "category": row["category"],
        "departmentId": row.get("department_id"),
        "userPrompt": row["user_prompt"],
        "prompt": row["prompt"],
        "optimizer": row["optimizer"],
        "mostUsedPromptCount": row["most_used_prompt_count"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "customFields": custom_fields or {},
        "tags": tags or [],
        "status": row.get("status", "approved"),
        "approvedAt": row.get("approved_at"),
        "approvedBy": row.get("approved_by"),
        "avgRating": rating.get("avg"),
        "ratingCount": rating.get("count", 0),
        "myRating": rating.get("mine"),
        "sourceType": row.get("source_type"),
        "sourceName": row.get("source_name"),
        "sourceContext": row.get("source_context"),
    }


def _blank_to_none(v: str | None) -> str | None:
    # An HTML <select>'s "Unassigned" option submits "" rather than omitting
    # the field or sending null -- treat it the same as "no department".
    return v or None


class PromptCreate(BaseModel):
    category: str
    userPrompt: str = Field(alias="userPrompt")
    prompt: str
    optimizer: str | None = None
    departmentId: str | None = None
    sourceType: Literal["file", "url"] | None = None
    sourceName: str | None = None
    sourceContext: str | None = None

    _normalize_department = field_validator("departmentId")(_blank_to_none)


class PromptUpdate(BaseModel):
    category: str | None = None
    userPrompt: str | None = None
    prompt: str | None = None
    optimizer: str | None = None
    departmentId: str | None = None

    _normalize_department = field_validator("departmentId")(_blank_to_none)


class PromptStatusUpdate(BaseModel):
    status: Literal["draft", "review", "approved", "archived"]


class RatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)
