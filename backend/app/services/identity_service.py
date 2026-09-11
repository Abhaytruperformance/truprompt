"""Maps WorkOS SSO profiles to TruPrompt users via `external_identities`.

Deliberately does NOT auto-link by matching profile.email against an existing
user's email -- identity linking is security-sensitive, and WorkOS's SSO
Profile carries no verified-email signal this codebase can trust (confirmed
directly against the installed SDK's Profile type: no email_verified field
exists). Auto-linking on a bare email match would let an attacker whose IdP
profile merely claims someone else's email get silently merged into that
person's real account. A WorkOS login always either matches an existing
linked identity or creates a brand-new user -- never a silent merge. A real
invited user still joins normally through the existing token-based
invitation-accept flow (app/services/org_service.py's accept_invitation).
"""

from datetime import datetime, timezone

from postgrest.exceptions import APIError
from workos.types.sso import Profile

from app.db.supabase import supabase


class EmailAlreadyExists(Exception):
    """Raised when a WorkOS profile's email matches an existing user who
    doesn't already have this WorkOS identity linked. Deliberately NOT
    auto-linked (see module docstring) -- surfaced as a clear, actionable
    error instead of a raw DB constraint violation."""


def upsert_user_from_workos_profile(profile: Profile) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    name = profile.name or " ".join(filter(None, [profile.first_name, profile.last_name])) or "Unknown"

    existing = (
        supabase.table("external_identities")
        .select("user_id")
        .eq("provider", "workos")
        .eq("subject", profile.id)
        .limit(1)
        .execute()
    )
    rows = existing.data or []

    if rows:
        user_id = rows[0]["user_id"]
        updated = (
            supabase.table("users")
            .update({"name": name, "email": profile.email, "updated_at": now})
            .eq("id", user_id)
            .execute()
        )
        return updated.data[0]

    try:
        inserted = supabase.table("users").insert({"name": name, "email": profile.email}).execute()
    except APIError as exc:
        if exc.code == "23505":  # unique_violation
            raise EmailAlreadyExists(
                f"An account with the email '{profile.email}' already exists."
            ) from exc
        raise
    user = inserted.data[0]
    supabase.table("external_identities").insert(
        {"user_id": user["id"], "provider": "workos", "subject": profile.id}
    ).execute()
    return user
