import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user, require_role
from app.schemas.department import DepartmentCreate, department_to_dict
from app.services.department_service import create_department, delete_department, list_departments

router = APIRouter()


@router.get("/")
def get_departments(current_user: dict = Depends(get_current_user)):
    rows = list_departments(current_user["org_id"])
    return {"departments": [department_to_dict(row) for row in rows]}


@router.post("/")
def create_department_route(
    body: DepartmentCreate, current_user: dict = Depends(require_role("admin"))
):
    try:
        row = create_department(current_user["org_id"], body.name)
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A department with this name already exists"
        )
    return department_to_dict(row)


@router.delete("/{department_id}")
def delete_department_route(
    department_id: str, current_user: dict = Depends(require_role("admin"))
):
    row = delete_department(current_user["org_id"], department_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department_to_dict(row)
