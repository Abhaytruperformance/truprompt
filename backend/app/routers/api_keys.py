from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_role
from app.schemas.api_key import ApiKeyCreate, api_key_to_dict
from app.services.api_key_service import create_api_key, list_api_keys, revoke_api_key
from app.services.audit_service import Action, ResourceType, log_audit_event

router = APIRouter()


@router.get("/")
def get_api_keys(current_user: dict = Depends(require_role("admin"))):
    rows = list_api_keys(current_user["org_id"])
    return {"apiKeys": [api_key_to_dict(row) for row in rows]}


@router.post("/")
def create_api_key_route(body: ApiKeyCreate, current_user: dict = Depends(require_role("admin"))):
    row, plaintext_key = create_api_key(
        current_user["org_id"], body.name, current_user["id"], body.expiresInDays, body.scopes
    )
    log_audit_event(
        current_user["org_id"], current_user["id"], Action.API_KEY_CREATED, ResourceType.API_KEY, row["id"],
        {"name": body.name, "scopes": row.get("scopes"), "legacy": False},
    )
    # The only time the plaintext is ever returned -- gone from the server
    # after this response, only the hash remains.
    return {**api_key_to_dict(row), "key": plaintext_key}


@router.delete("/{key_id}")
def revoke_api_key_route(key_id: str, current_user: dict = Depends(require_role("admin"))):
    row = revoke_api_key(current_user["org_id"], key_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    log_audit_event(current_user["org_id"], current_user["id"], Action.API_KEY_REVOKED, ResourceType.API_KEY, key_id)
    return api_key_to_dict(row)
