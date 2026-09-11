import openai
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.schemas.prompt import prompt_to_dict
from app.services.analytics_service import log_generation_event
from app.services.openai_service import generate_prompt
from app.services.share_service import (
    ShareNotFound,
    SharePasswordError,
    TooManyAttempts,
    current_version_number_public,
    get_prompt_public,
    release_generation_count,
    try_increment_generation_count,
    unlock_share,
)

router = APIRouter()


class UnlockShare(BaseModel):
    password: str | None = None


def _unlock_or_404(token: str, password: str | None) -> dict:
    # POST + body (not a GET query param) so a share password never ends up
    # in a URL -- query strings get logged server-side, kept in browser
    # history, and can leak via the Referer header.
    try:
        return unlock_share(token, password)
    except ShareNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SharePasswordError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except TooManyAttempts as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))


@router.post("/shares/{token}")
def get_public_share(token: str, body: UnlockShare = UnlockShare()):
    share = _unlock_or_404(token, body.password)

    prompt_row = get_prompt_public(share["prompt_id"])
    if not prompt_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    return {"prompt": prompt_to_dict(prompt_row)}


@router.post("/shares/{token}/generate")
def generate_from_share(token: str, body: UnlockShare = UnlockShare()):
    """Regenerates a fresh AI-crafted prompt from a public share link --
    read-only, does not overwrite the stored prompt (same semantics as the
    app's own "regenerate" button and the authenticated public API's
    /v1/prompts/{id}/generate). Gated by the same password check as viewing
    the share, plus generation_limit if the share creator set one."""
    share = _unlock_or_404(token, body.password)

    prompt_row = get_prompt_public(share["prompt_id"])
    if not prompt_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    # Archiving means "retired, don't build on this anymore" -- same rule as
    # the authenticated public API's generate endpoint.
    if prompt_row["status"] == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This prompt is archived and can no longer be generated from.",
        )

    # Checked (and reserved) before calling the LLM -- a request that would
    # exceed the limit never wastes a real generation call.
    if not try_increment_generation_count(share["id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This share link has reached its generation limit.",
        )

    # The actual invariant is "release the reservation unless a successful
    # generation was produced" -- not "release for these two known OpenAI
    # exception types." try/finally covers every failure path (timeouts,
    # SDK/parsing errors, anything else), not just the ones anticipated here.
    succeeded = False
    try:
        try:
            result = generate_prompt(prompt_row["user_prompt"], prompt_row["category"].split(", "))
        except openai.RateLimitError:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="The AI provider is temporarily rate-limited. Please try again in a moment.",
            )
        except openai.APIError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI provider returned an error. Please try again.",
            )
        succeeded = True
    finally:
        if not succeeded:
            release_generation_count(share["id"])

    # A best-effort analytics-write failure here must not refund the
    # generation -- the visitor already has their result.
    log_generation_event(
        share["org_id"], None, share["prompt_id"], "share", result.get("modelUsed"),
        current_version_number_public(share["prompt_id"]),
    )
    return {"optimizer": result["optimizer"], "prompt": result["prompt"]}
