import html

import httpx

from app.core.config import settings

RESEND_API_URL = "https://api.resend.com/emails"


def send_invitation_email(to_email: str, org_name: str, token: str) -> None:
    accept_link = f"{settings.FRONTEND_URL}/accept-invite?token={token}"

    if settings.RESEND_API_KEY.startswith("placeholder-"):
        # No real Resend key yet -- log instead of failing the invite request.
        print(f"[email stub] invite {to_email} to {org_name}: {accept_link}")
        return

    # org_name is user-controlled (set at org creation, editable later) --
    # escape before interpolating into the HTML body so a malicious org name
    # can't inject markup/scripts into an email sent to someone else.
    safe_org_name = html.escape(org_name)
    safe_accept_link = html.escape(accept_link, quote=True)

    httpx.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
        json={
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": f"You've been invited to {org_name} on TruPrompt",
            "html": (
                f"<p>You've been invited to join <strong>{safe_org_name}</strong> on TruPrompt.</p>"
                f'<p><a href="{safe_accept_link}">Accept invitation</a></p>'
            ),
        },
        timeout=10.0,
    ).raise_for_status()
