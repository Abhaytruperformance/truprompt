import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.auth.dependencies import get_current_user, get_current_user_optional
from app.auth.microsoft import (
    build_authorization_url,
    exchange_code_for_profile,
    upsert_user_from_profile,
)
from app.core.config import settings
from app.core.security import (
    STATE_COOKIE_NAME,
    clear_auth_cookie,
    clear_state_cookie,
    set_auth_cookie,
    set_state_cookie,
)
from app.db.supabase import supabase
from app.schemas.user import user_to_dict
from app.services.org_service import ensure_org_for_user

router = APIRouter()


@router.get("/auth/microsoft")
def microsoft_auth(request: Request, code: str | None = None, state: str | None = None):
    # 1. OAuth callback from Microsoft (has ?code=...)
    if code:
        # CSRF check: `state` must match what we generated and stashed in a
        # cookie before redirecting to Microsoft (see branch 3). Without this,
        # an attacker could complete their own OAuth flow, get a valid code for
        # *their* Microsoft account, then trick a victim's browser into hitting
        # this callback with it -- logging the victim in as the attacker.
        expected_state = request.cookies.get(STATE_COOKIE_NAME)
        state_ok = bool(expected_state) and secrets.compare_digest(expected_state, state or "")

        if not state_ok:
            redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=sso_failed")
            clear_state_cookie(redirect)
            return redirect

        try:
            profile = exchange_code_for_profile(code)
            user = upsert_user_from_profile(profile)
        except Exception:
            redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=sso_failed")
            clear_state_cookie(redirect)
            return redirect

        org_id = ensure_org_for_user(user)
        redirect = RedirectResponse(url=settings.FRONTEND_URL)
        set_auth_cookie(redirect, user["id"], org_id)
        clear_state_cookie(redirect)
        return redirect

    # 2. Background session check (RTK Query `useMicrosoftLoginQuery`, has a valid cookie)
    user = get_current_user_optional(request)
    if user:
        return {"user": user_to_dict(user)}

    # 3. Full-page navigation from the "Login with Microsoft" button (no cookie yet)
    if "text/html" in request.headers.get("accept", ""):
        oauth_state = secrets.token_urlsafe(32)
        redirect = RedirectResponse(url=build_authorization_url(oauth_state))
        set_state_cookie(redirect, oauth_state)
        return redirect

    # 4. Background session check with no cookie -> let the frontend show LoginScreen
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@router.get("/auth/dev-login")
def dev_login():
    """DEBUG-only bypass for local development: logs in as a fixed test user
    without an Azure AD round-trip. Disabled (404) whenever DEBUG is false."""
    if not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    fake_profile = {
        "id": "dev-local-user",
        "displayName": "Dev User",
        "mail": "dev@local.test",
    }
    user = upsert_user_from_profile(fake_profile)
    org_id = ensure_org_for_user(user)

    redirect = RedirectResponse(url=settings.FRONTEND_URL)
    set_auth_cookie(redirect, user["id"], org_id)
    return redirect


@router.get("/auth/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "logged out"}


@router.get("/allusers")
def all_users(current_user: dict = Depends(get_current_user)):
    # Scoped to the caller's own org, not every user in the system -- this used
    # to return everyone before multi-tenancy existed, which would otherwise
    # leak every other customer's employees' names/emails across org boundaries.
    member_rows = (
        supabase.table("organization_members")
        .select("user_id")
        .eq("org_id", current_user["org_id"])
        .execute()
        .data
        or []
    )
    user_ids = [row["user_id"] for row in member_rows]
    if not user_ids:
        return {"allUsers": []}

    result = supabase.table("users").select("*").in_("id", user_ids).execute()
    return {"allUsers": [user_to_dict(row) for row in (result.data or [])]}
