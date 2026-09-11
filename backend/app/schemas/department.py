from pydantic import BaseModel


def department_to_dict(row: dict) -> dict:
    return {
        "_id": row["id"],
        "orgId": row["org_id"],
        "name": row["name"],
        "createdAt": row["created_at"],
    }


class DepartmentCreate(BaseModel):
    name: str
