import openai
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.api_key import ApiKeyScope, require_api_key_scope
from app.db.pg import org_scoped_cursor
from app.routers.prompts import _get_org_prompt_row_or_404
from app.services.analytics_service import log_generation_event
from app.services.openai_service import generate_prompt
from app.services.version_service import current_version_number

router = APIRouter()


class PublicGenerateResponse(BaseModel):
    optimizer: str = Field(description="Bullet-point context/goals behind the generated prompt")
    prompt: str = Field(description="The freshly generated, well-crafted prompt text")


@router.post(
    "/prompts/{prompt_id}/generate",
    response_model=PublicGenerateResponse,
    summary="Regenerate a fresh AI-crafted prompt for one of your organization's saved prompts",
    description=(
        "Authenticated via `Authorization: Bearer <api_key>`. Re-runs generation using the "
        "saved prompt's original request and category -- read-only, does not overwrite the "
        "stored prompt (same semantics as the app's own 'regenerate' button). Requires the "
        "key's `prompts:generate` scope."
    ),
    responses={
        403: {
            "description": "The API key doesn't carry the required scope.",
            "content": {"application/json": {"example": {"detail": "Missing required scope: prompts:generate"}}},
        },
    },
)
def public_generate(prompt_id: str, org_id: str = Depends(require_api_key_scope(ApiKeyScope.GENERATE))):
    with org_scoped_cursor(org_id) as cur:
        row = _get_org_prompt_row_or_404(cur, prompt_id)
        version_number = current_version_number(cur, prompt_id)

    # Archiving means "retired, don't build on this anymore" -- reading an
    # archived prompt is still fine (nothing about viewing is destructive
    # elsewhere in this app), but generating more from it defeats the point
    # of archiving it in the first place.
    if row["status"] == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This prompt is archived and can no longer be generated from.",
        )

    try:
        result = generate_prompt(row["user_prompt"], row["category"].split(", "))
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

    log_generation_event(org_id, None, prompt_id, "api", result.get("modelUsed"), version_number)
    return {"optimizer": result["optimizer"], "prompt": result["prompt"]}
