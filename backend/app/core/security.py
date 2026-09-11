from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Response

from app.core.config import settings

COOKIE_NAME = "token"
STATE_COOKIE_NAME = "ms_oauth_state"
STATE_COOKIE_MAX_AGE = 600  # 10 minutes -- only needs to survive the redirect round-trip


def create_access_token(user_id: str, org_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "org_id": org_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Returns {"user_id": ..., "org_id": ...} or None if the token is missing/invalid."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if "sub" not in payload or "org_id" not in payload:
        return None
    return {"user_id": payload["sub"], "org_id": payload["org_id"]}


def set_auth_cookie(response: Response, user_id: str, org_id: str) -> None:
    token = create_access_token(user_id, org_id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax" if settings.DEBUG else "none",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=not settings.DEBUG,
        samesite="lax" if settings.DEBUG else "none",
    )


def set_state_cookie(response: Response, state: str) -> None:
    """CSRF protection for the Microsoft OAuth flow: a random value we generate,
    stash in a short-lived cookie, and require to come back unmodified in the
    callback's `state` query param -- without this, an attacker could get their
    own valid Microsoft auth code and trick a victim's browser into completing
    the callback with it, logging the victim in as the attacker's identity."""
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax" if settings.DEBUG else "none",
        max_age=STATE_COOKIE_MAX_AGE,
        path="/",
    )


def clear_state_cookie(response: Response) -> None:
    response.delete_cookie(
        key=STATE_COOKIE_NAME,
        path="/",
        secure=not settings.DEBUG,
        samesite="lax" if settings.DEBUG else "none",
    )
