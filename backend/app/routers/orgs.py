import secrets

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.auth.dependencies import get_current_user, require_role
from app.auth.workos import build_authorization_url, connection_exists, exchange_code_for_profile
from app.core.config import settings
from app.core.security import (
    STATE_COOKIE_NAME,
    clear_state_cookie,
    set_auth_cookie,
    set_state_cookie,
)
from app.db.pg import org_scoped_cursor
from app.db.supabase import supabase
from app.schemas.org import (
    AcceptInvite,
    InviteCreate,
    RoleUpdate,
    WorkosConnectionUpdate,
    invitation_to_dict,
    membership_to_dict,
    org_to_dict,
)
from app.services.analytics_service import get_org_analytics
from app.services.audit_service import Action, ResourceType, log_audit_event
from app.services.email_service import send_invitation_email
from app.services.identity_service import EmailAlreadyExists, upsert_user_from_workos_profile
from app.services.org_service import (
    accept_invitation,
    create_invitation,
    ensure_org_membership,
    get_org_by_slug,
    get_org_by_workos_connection_id,
    set_workos_connection,
)

router = APIRouter()


@router.get("/me")
def get_my_org(current_user: dict = Depends(get_current_user)):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute("select * from organizations where id = %s limit 1", (current_user["org_id"],))
        org = cur.fetchone()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return {"organization": org_to_dict(org), "role": current_user["role"]}


@router.get("/analytics")
def get_analytics(current_user: dict = Depends(require_role("admin"))):
    return get_org_analytics(current_user["org_id"])


@router.put("/me/workos-connection")
def update_workos_connection(
    body: WorkosConnectionUpdate, current_user: dict = Depends(require_role("admin"))
):
    # An admin can't attach a made-up or mistyped connection id -- confirm
    # WorkOS actually recognizes it before it's ever saved.
    if body.connectionId and not connection_exists(body.connectionId):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WorkOS doesn't recognize this connection id",
        )
    try:
        org = set_workos_connection(current_user["org_id"], current_user["id"], body.connectionId)
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This connection is already used by another organization",
        )
    log_audit_event(
        current_user["org_id"], current_user["id"], Action.SSO_CONNECTION_CHANGED, ResourceType.ORGANIZATION,
        current_user["org_id"], {"connectionId": body.connectionId},
    )
    return org_to_dict(org)


@router.get("/auth/workos")
def workos_auth(request: Request, org: str | None = None, code: str | None = None, state: str | None = None):
    # 1. OAuth callback from WorkOS (has ?code=&state=)
    if code:
        # CSRF check, same shape as the Microsoft flow (app/routers/users.py) --
        # `state` was generated and stashed in a cookie before redirecting to
        # WorkOS (see branch 2 below).
        expected_state = request.cookies.get(STATE_COOKIE_NAME)
        state_ok = bool(expected_state) and secrets.compare_digest(expected_state, state or "")
        if not state_ok:
            redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=sso_failed")
            clear_state_cookie(redirect)
            return redirect

        # The connection id used at initiation is bound into the state value
        # itself ("<nonce>.<connection_id>") -- verified again below against
        # what WorkOS actually returns, closing the gap where a login flow
        # initiated for one connection could otherwise complete against a
        # different one (e.g. if an org's connection was reconfigured
        # mid-flow, or WorkOS returned an unexpected connection).
        _, _, expected_connection_id = expected_state.partition(".")

        try:
            profile = exchange_code_for_profile(code)
        except Exception:
            redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=sso_failed")
            clear_state_cookie(redirect)
            return redirect

        if profile.connection_id != expected_connection_id:
            redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=sso_failed")
            clear_state_cookie(redirect)
            return redirect

        # Org is resolved from WorkOS's own authenticated response, never from
        # a client-supplied ?org= -- a forged initiate param can't attribute a
        # login to the wrong org.
        org_row = get_org_by_workos_connection_id(profile.connection_id)
        if not org_row:
            redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=sso_failed")
            clear_state_cookie(redirect)
            return redirect

        try:
            user = upsert_user_from_workos_profile(profile)
        except EmailAlreadyExists:
            # Deliberately not auto-linked (see identity_service's module
            # docstring) -- fails cleanly instead of a raw DB error.
            redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=email_exists")
            clear_state_cookie(redirect)
            return redirect

        # JIT provisioning: a successful login through this org's configured
        # IdP automatically grants membership (never downgrades an existing one).
        ensure_org_membership(org_row["id"], user["id"])

        redirect = RedirectResponse(url=settings.FRONTEND_URL)
        set_auth_cookie(redirect, user["id"], org_row["id"])
        clear_state_cookie(redirect)
        return redirect

    # 2. Full-page navigation from a "Continue with company SSO" button (no code yet)
    if not org:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing org")

    org_row = get_org_by_slug(org)
    if not org_row or not org_row.get("workos_connection_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured for this organization"
        )

    connection_id = org_row["workos_connection_id"]
    oauth_state = f"{secrets.token_urlsafe(24)}.{connection_id}"
    redirect = RedirectResponse(url=build_authorization_url(connection_id, oauth_state))
    set_state_cookie(redirect, oauth_state)
    return redirect


@router.get("/members")
def list_members(current_user: dict = Depends(get_current_user)):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute("select * from organization_members where org_id = %s", (current_user["org_id"],))
        members = cur.fetchall()

    # users isn't RLS-scoped (see README "Isolation") -- this join stays on the
    # existing service-role client, unchanged from before.
    user_ids = [m["user_id"] for m in members]
    users_by_id = {}
    if user_ids:
        rows = supabase.table("users").select("*").in_("id", user_ids).execute().data or []
        users_by_id = {row["id"]: row for row in rows}

    return {"members": [membership_to_dict(m, users_by_id.get(m["user_id"])) for m in members]}


@router.patch("/members/{user_id}")
def update_member_role(
    user_id: str, body: RoleUpdate, current_user: dict = Depends(require_role("admin"))
):
    if body.role == "owner" and current_user["role"] != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can grant the owner role"
        )

    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute(
            "select role from organization_members where org_id = %s and user_id = %s",
            (current_user["org_id"], user_id),
        )
        target = cur.fetchone()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        # An admin (not owner) could otherwise strip an owner's role entirely --
        # only an owner may change another owner's role at all, not just grant it.
        if target["role"] == "owner" and current_user["role"] != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an owner can modify another owner",
            )

        # Never let the org end up with zero owners.
        if target["role"] == "owner" and body.role != "owner":
            cur.execute(
                "select count(*) as c from organization_members where org_id = %s and role = 'owner'",
                (current_user["org_id"],),
            )
            if cur.fetchone()["c"] <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the org's last owner",
                )

        cur.execute(
            """update organization_members set role = %s where org_id = %s and user_id = %s
               returning *""",
            (body.role, current_user["org_id"], user_id),
        )
        updated = cur.fetchone()
    log_audit_event(
        current_user["org_id"], current_user["id"], Action.MEMBER_ROLE_CHANGED, ResourceType.MEMBER, user_id,
        {"from": target["role"], "to": body.role},
    )
    return membership_to_dict(updated)


@router.get("/invitations")
def list_invitations(current_user: dict = Depends(require_role("admin"))):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute(
            "select * from invitations where org_id = %s and accepted_at is null",
            (current_user["org_id"],),
        )
        rows = cur.fetchall()
    return {"invitations": [invitation_to_dict(row) for row in rows]}


@router.post("/invitations")
def invite_member(body: InviteCreate, current_user: dict = Depends(require_role("admin"))):
    if body.role == "owner" and current_user["role"] != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can invite as owner"
        )
    invitation = create_invitation(
        current_user["org_id"], body.email, body.role, current_user["id"]
    )

    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute("select name from organizations where id = %s limit 1", (current_user["org_id"],))
        org = cur.fetchone()
    org_name = org["name"] if org else "TruPrompt"
    try:
        send_invitation_email(body.email, org_name, invitation["token"])
    except Exception as e:
        # The invitation itself already committed -- a delivery failure (e.g.
        # Resend's sandbox mode rejecting non-verified recipients) shouldn't
        # 500 the whole request and hide the invite that was actually created.
        print(f"[email] failed to send invitation to {body.email}: {e}")

    return invitation_to_dict(invitation)


@router.delete("/invitations/{invitation_id}")
def cancel_invitation(invitation_id: str, current_user: dict = Depends(require_role("admin"))):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute(
            """delete from invitations where id = %s and org_id = %s and accepted_at is null
               returning *""",
            (invitation_id, current_user["org_id"]),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    return invitation_to_dict(row)


@router.post("/invitations/accept")
def accept_invite(body: AcceptInvite, current_user: dict = Depends(get_current_user)):
    try:
        invitation = accept_invitation(body.token, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return invitation_to_dict(invitation)
