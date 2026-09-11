import openai
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.schemas.ai import ExtractUrlRequest, GeneratePromptRequest
from app.services.content_extraction_service import (
    ExtractionFailed,
    FetchError,
    ResponseTooLarge,
    UnsafeUrl,
    UnsupportedContentType,
    UnsupportedFileType,
    extract_from_file,
    extract_from_url,
)
from app.services.analytics_service import log_generation_event
from app.services.openai_service import InvalidModel, generate_prompt, list_available_models

router = APIRouter()


@router.get("/models")
def get_models(current_user: dict = Depends(get_current_user)):
    return {"models": list_available_models()}


@router.post("/extract-file")
async def extract_file_route(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )
    try:
        result = extract_from_file(file.filename or "", content)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ExtractionFailed as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return {**result, "sourceType": "file", "sourceName": file.filename}


@router.post("/extract-url")
def extract_url_route(body: ExtractUrlRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = extract_from_url(body.url)
    except (UnsafeUrl, UnsupportedContentType) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ResponseTooLarge as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))
    except FetchError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return {**result, "sourceType": "url", "sourceName": body.url}


@router.post("/generate-prompt")
def generate_prompt_route(body: GeneratePromptRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = generate_prompt(
            body.userPrompt, body.selectedOptions, body.model, body.extraContext, body.allowFallback
        )
        # No prompt_id -- New Chat/Playground generations aren't tied to a
        # saved prompt yet at generation time. Best-effort (see
        # log_generation_event's docstring): never turns a real generation
        # into an error response.
        log_generation_event(current_user["org_id"], current_user["id"], None, "web", result.get("modelUsed"))
        return result
    except InvalidModel as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except openai.RateLimitError:
        # Free-tier models share a provider-side quota (not per-user) -- this
        # is expected to happen occasionally, not a server bug, so it gets a
        # real 429 with an actionable message instead of a raw 500.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI provider is temporarily rate-limited. Please try again in a moment.",
        )
    except openai.APIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an error. Please try again.",
        )
