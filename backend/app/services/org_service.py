import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.db.pg import org_scoped_cursor
from app.db.supabase import supabase

ROLE_RANK = {"member": 0, "editor": 1, "admin": 2, "owner": 3}
INVITATION_EXPIRE_DAYS = 7

# Authorization matrix -- the expected contract, kept next to ROLE_RANK
# instead of a separate doc that can drift further out of sync. The actual
# require_role()/ROLE_RANK checks scattered across the routers remain the
# real source of truth; this documents what they're supposed to add up to.
# When automated tests exist, this table should drive a parametrized test
# that proves the code matches it -- until then, it's a contract to check
# new admin-gated actions against by hand, not a guarantee enforced anywhere.
#
#   Operation                        Member  Editor  Admin  Owner
#   --------------------------------------------------------------
#   Generate a prompt                  Y       Y       Y      Y
#   Create/edit any org prompt         -       Y       Y      Y
#   Submit for review / withdraw       -       Y       Y      Y
#   Approve / archive a prompt         -       -       Y      Y
#   Restore a prompt version           -       Y       Y      Y
#   Create/revoke a share link         -       Y       Y      Y
#   Invite a member                    -       -       Y      Y
#   Change a member's role             -       -       Y*     Y
#     (* an admin cannot touch another admin/owner's role, or grant owner)
#   Create/revoke an API key           -       -       Y      Y
#   Configure WorkOS SSO connection    -       -       Y      Y
#
# "Member" (rank 0) is intentionally read/generate-only -- everything that
# writes to the shared org library requires "editor" (rank 1) or above.


def _slugify(name: str, suffix: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "org"
    return f"{base}-{suffix}"


def get_membership(user_id: str, org_id: str) -> dict | None:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "select * from organization_members where user_id = %s and org_id = %s limit 1",
            (user_id, org_id),
        )
        return cur.fetchone()


def list_memberships(user_id: str) -> list[dict]:
    # "Which orgs do I belong to" can't be scoped to a single org_id -- that's
    # the very thing being discovered here -- so this stays on the service-role
    # client rather than the RLS-scoped connection. Filtering by the caller's
    # own user_id keeps this safe (never returns another user's memberships).
    result = supabase.table("organization_members").select("*").eq("user_id", user_id).execute()
    return result.data or []


def create_org_for_user(user: dict) -> dict:
    """Auto-provisions a personal organization for a brand-new user (no invitation flow yet).
    Generates the org's id client-side so app.org_id can be set *before* the
    organizations insert -- avoids a chicken-and-egg problem with RLS."""
    org_id = str(uuid.uuid4())
    slug = _slugify(user["name"] or user["email"], secrets.token_hex(3))
    name = f"{user['name']}'s Organization"

    with org_scoped_cursor(org_id, user["id"]) as cur:
        cur.execute(
            "insert into organizations (id, name, slug) values (%s, %s, %s) returning *",
            (org_id, name, slug),
        )
        org = cur.fetchone()
        cur.execute(
            "insert into organization_members (org_id, user_id, role) values (%s, %s, 'owner')",
            (org_id, user["id"]),
        )

    supabase.table("users").update({"last_active_org_id": org_id}).eq("id", user["id"]).execute()
    return org


def ensure_org_for_user(user: dict) -> str:
    """Returns the org_id a login should mint a token for: the user's last-active
    org if they belong to one, otherwise a freshly auto-provisioned org."""
    if user.get("last_active_org_id"):
        membership = get_membership(user["id"], user["last_active_org_id"])
        if membership:
            return user["last_active_org_id"]

    memberships = list_memberships(user["id"])
    if memberships:
        org_id = memberships[0]["org_id"]
        supabase.table("users").update({"last_active_org_id": org_id}).eq(
            "id", user["id"]
        ).execute()
        return org_id

    return create_org_for_user(user)["id"]


def get_org_by_slug(slug: str) -> dict | None:
    # Which org this is is exactly what's being discovered here, so this stays
    # on the service-role client, same precedent as list_memberships/accept_invitation.
    result = supabase.table("organizations").select("*").eq("slug", slug).limit(1).execute()
    rows = result.data or []
    return rows[0] if rows else None


def get_org_by_workos_connection_id(connection_id: str) -> dict | None:
    result = (
        supabase.table("organizations")
        .select("*")
        .eq("workos_connection_id", connection_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def ensure_org_membership(org_id: str, user_id: str, role: str = "member") -> None:
    """Insert-if-not-exists only -- never updates an existing membership's
    role. This is the deliberate JIT-provisioning policy for WorkOS SSO logins
    (see app/routers/orgs.py's workos_auth): a successful login through an
    org's configured IdP automatically grants membership, but must never
    silently downgrade someone who already has a higher role (e.g. via a
    prior invitation)."""
    with org_scoped_cursor(org_id, user_id) as cur:
        cur.execute(
            "select 1 from organization_members where org_id = %s and user_id = %s",
            (org_id, user_id),
        )
        if cur.fetchone():
            return
        cur.execute(
            "insert into organization_members (org_id, user_id, role) values (%s, %s, %s)",
            (org_id, user_id, role),
        )


def set_workos_connection(org_id: str, user_id: str, connection_id: str | None) -> dict:
    """Raises psycopg2.errors.UniqueViolation if connection_id is already
    claimed by a different org (caught by the router, same pattern as
    departments/tags/custom_fields' name-uniqueness handling)."""
    with org_scoped_cursor(org_id, user_id) as cur:
        cur.execute(
            "update organizations set workos_connection_id = %s where id = %s returning *",
            (connection_id, org_id),
        )
        return cur.fetchone()


def create_invitation(org_id: str, email: str, role: str, invited_by: str) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRE_DAYS)

    with org_scoped_cursor(org_id, invited_by) as cur:
        cur.execute(
            """insert into invitations (org_id, email, role, token, invited_by, expires_at)
               values (%s, %s, %s, %s, %s, %s) returning *""",
            (org_id, email, role, token, invited_by, expires_at),
        )
        return cur.fetchone()


def accept_invitation(token: str, user: dict) -> dict:
    # The accepting user doesn't know their org_id yet -- that's what the token
    # is for -- so this one narrow lookup has to happen before app.org_id can
    # be set to anything. Possessing the random unguessable token is itself
    # the authorization for this specific read; stays on the service-role client.
    result = (
        supabase.table("invitations")
        .select("*")
        .eq("token", token)
        .is_("accepted_at", "null")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise ValueError("Invalid or already-used invitation")

    invitation = rows[0]
    expires_at = datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise ValueError("Invitation has expired")

    org_id = invitation["org_id"]
    with org_scoped_cursor(org_id, user["id"]) as cur:
        if not get_membership(user["id"], org_id):
            cur.execute(
                "insert into organization_members (org_id, user_id, role) values (%s, %s, %s)",
                (org_id, user["id"], invitation["role"]),
            )
        cur.execute(
            "update invitations set accepted_at = now() where id = %s",
            (invitation["id"],),
        )

    supabase.table("users").update({"last_active_org_id": org_id}).eq("id", user["id"]).execute()
    return invitation
