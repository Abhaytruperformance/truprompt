from datetime import datetime, timezone

import httpx
import msal

from app.core.config import settings
from app.db.supabase import supabase

GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"
SCOPES = ["User.Read"]


def _msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=settings.MS_CLIENT_ID,
        client_credential=settings.MS_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}",
    )


def build_authorization_url(state: str) -> str:
    return _msal_app().get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=settings.MS_REDIRECT_URI,
        state=state,
    )


def exchange_code_for_profile(code: str) -> dict:
    """Exchanges an OAuth authorization code for the caller's Microsoft Graph profile."""
    result = _msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=settings.MS_REDIRECT_URI,
    )
    if "access_token" not in result:
        raise ValueError(result.get("error_description", "Microsoft SSO token exchange failed"))

    response = httpx.get(
        GRAPH_ME_URL,
        headers={"Authorization": f"Bearer {result['access_token']}"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def upsert_user_from_profile(profile: dict) -> dict:
    microsoft_oid = profile["id"]
    name = profile.get("displayName") or "Unknown"
    email = profile.get("mail") or profile.get("userPrincipalName")
    now = datetime.now(timezone.utc).isoformat()

    existing = (
        supabase.table("users").select("*").eq("microsoft_oid", microsoft_oid).limit(1).execute()
    )
    rows = existing.data or []

    if rows:
        user_id = rows[0]["id"]
        updated = (
            supabase.table("users")
            .update({"name": name, "email": email, "updated_at": now})
            .eq("id", user_id)
            .execute()
        )
        return updated.data[0]

    inserted = (
        supabase.table("users")
        .insert({"microsoft_oid": microsoft_oid, "name": name, "email": email})
        .execute()
    )
    return inserted.data[0]
