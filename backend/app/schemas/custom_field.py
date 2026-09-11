from pydantic import BaseModel


def field_def_to_dict(row: dict) -> dict:
    return {
        "_id": row["id"],
        "orgId": row["org_id"],
        "name": row["name"],
        "fieldType": row["field_type"],
        "options": row["options"],
        "createdAt": row["created_at"],
    }


class CustomFieldCreate(BaseModel):
    name: str
    fieldType: str = "text"
    options: list[str] | None = None


class CustomFieldValuesUpdate(BaseModel):
    values: dict[str, str]
