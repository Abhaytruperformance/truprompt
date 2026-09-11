from pydantic import BaseModel


def org_to_dict(row: dict) -> dict:
    return {
        "_id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "createdAt": row["created_at"],
        "workosConnectionId": row.get("workos_connection_id"),
    }


def membership_to_dict(row: dict, user_row: dict | None = None) -> dict:
    data = {
        "_id": row["id"],
        "orgId": row["org_id"],
        "userId": row["user_id"],
        "role": row["role"],
    }
    if user_row:
        data["name"] = user_row["name"]
        data["email"] = user_row["email"]
    return data


def invitation_to_dict(row: dict) -> dict:
    return {
        "_id": row["id"],
        "orgId": row["org_id"],
        "email": row["email"],
        "role": row["role"],
        "token": row["token"],
        "expiresAt": row["expires_at"],
        "acceptedAt": row.get("accepted_at"),
    }


class InviteCreate(BaseModel):
    email: str
    role: str = "member"


class AcceptInvite(BaseModel):
    token: str


class RoleUpdate(BaseModel):
    role: str


class WorkosConnectionUpdate(BaseModel):
    connectionId: str | None = None
