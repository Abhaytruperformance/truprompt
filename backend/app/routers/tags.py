import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user, require_role
from app.schemas.tag import TagCreate, tag_to_dict
from app.services.tag_service import create_tag, delete_tag, list_tags

router = APIRouter()


@router.get("/")
def get_tags(current_user: dict = Depends(get_current_user)):
    rows = list_tags(current_user["org_id"])
    return {"tags": [tag_to_dict(row) for row in rows]}


@router.post("/")
def create_tag_route(body: TagCreate, current_user: dict = Depends(require_role("admin"))):
    try:
        row = create_tag(current_user["org_id"], body.name)
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A tag with this name already exists"
        )
    return tag_to_dict(row)


@router.delete("/{tag_id}")
def delete_tag_route(tag_id: str, current_user: dict = Depends(require_role("admin"))):
    row = delete_tag(current_user["org_id"], tag_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag_to_dict(row)
