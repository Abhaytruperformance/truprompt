import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user, require_role
from app.schemas.custom_field import CustomFieldCreate, field_def_to_dict
from app.services.custom_field_service import create_field_def, delete_field_def, list_field_defs

router = APIRouter()


@router.get("/")
def get_custom_fields(current_user: dict = Depends(get_current_user)):
    rows = list_field_defs(current_user["org_id"])
    return {"customFields": [field_def_to_dict(row) for row in rows]}


@router.post("/")
def create_custom_field_route(
    body: CustomFieldCreate, current_user: dict = Depends(require_role("admin"))
):
    try:
        row = create_field_def(current_user["org_id"], body.name, body.fieldType, body.options)
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A custom field with this name already exists"
        )
    return field_def_to_dict(row)


@router.delete("/{field_def_id}")
def delete_custom_field_route(
    field_def_id: str, current_user: dict = Depends(require_role("admin"))
):
    row = delete_field_def(current_user["org_id"], field_def_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom field not found")
    return field_def_to_dict(row)
