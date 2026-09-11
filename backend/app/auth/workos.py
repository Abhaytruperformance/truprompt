"""WorkOS AuthKit -- lets a customer connect their own Okta/Azure AD/
Google Workspace as an identity provider for their organization.

Identity mapping decision (was previously an open question, now resolved):
a separate `external_identities` table maps `(provider, subject)` -> user_id,
rather than reusing/extending `users.microsoft_oid` -- a user can hold both
their own Microsoft SSO identity and a customer's WorkOS identity at once.
See `app/services/identity_service.py`.
"""

import workos
from workos import NotFoundError
from workos.types.sso import Profile

from app.core.config import settings

_client = workos.WorkOSClient(api_key=settings.WORKOS_API_KEY, client_id=settings.WORKOS_CLIENT_ID)


def build_authorization_url(connection_id: str, state: str) -> str:
    """`connection_id` is the WorkOS connection tied to one of our
    `organizations` rows (see `organizations.workos_connection_id`). `state`
    is a CSRF nonce with the connection id bound into it -- see
    `app/routers/orgs.py`'s `workos_auth` for why."""
    return _client.sso.get_authorization_url(
        connection=connection_id,
        redirect_uri=settings.WORKOS_REDIRECT_URI,
        state=state,
    )


def exchange_code_for_profile(code: str) -> Profile:
    """Returns the WorkOS Profile object (.id, .email, .first_name, .last_name,
    .organization_id, .connection_id, ...) -- shape differs from the Microsoft
    Graph profile dict `upsert_user_from_profile` expects."""
    return _client.sso.get_profile_and_token(code=code).profile


def connection_exists(connection_id: str) -> bool:
    """Used to validate an admin-supplied connection id before it's saved --
    an admin shouldn't be able to attach a made-up or mistyped id to their org."""
    try:
        _client.sso.get_connection(connection_id)
        return True
    except NotFoundError:
        return False
