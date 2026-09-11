from fastapi import Depends, HTTPException, Request, status

from app.core.security import COOKIE_NAME, decode_access_token
from app.db.supabase import supabase
from app.services.org_service import ROLE_RANK, get_membership


def _load_user_row(user_id: str) -> dict | None:
    result = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    rows = result.data or []
    return rows[0] if rows else None


def _resolve(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    claims = decode_access_token(token) if token else None
    if not claims:
        return None

    user = _load_user_row(claims["user_id"])
    if not user:
        return None

    membership = get_membership(claims["user_id"], claims["org_id"])
    if not membership:
        # org_id in the token is no longer valid (e.g. removed from the org) -
        # treat as logged out rather than trusting a stale claim.
        return None

    return {**user, "org_id": claims["org_id"], "role": membership["role"]}


def get_current_user(request: Request) -> dict:
    user = _resolve(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def get_current_user_optional(request: Request) -> dict | None:
    return _resolve(request)


def require_role(minimum: str):
    """Dependency factory: 401 if not logged in, 403 if role rank is below `minimum`."""

    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if ROLE_RANK.get(current_user["role"], -1) < ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum}+ role in this organization",
            )
        return current_user

    return _check
