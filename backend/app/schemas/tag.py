from pydantic import BaseModel


def tag_to_dict(row: dict) -> dict:
    return {
        "_id": row["id"],
        "orgId": row["org_id"],
        "name": row["name"],
        "createdAt": row["created_at"],
    }


class TagCreate(BaseModel):
    name: str


class PromptTagsUpdate(BaseModel):
    tagIds: list[str]
