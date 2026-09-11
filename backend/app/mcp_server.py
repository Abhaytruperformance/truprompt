"""MCP (Model Context Protocol) server exposing an org's TruPrompt data as
tools -- read + regenerate only, no writes. Authenticated the same way as the
public REST API (`app/routers/public_api.py`): `Authorization: Bearer <api_key>`.

API-key-header auth only, no OAuth -- works with Claude Code, Claude Desktop
(via a custom-header MCP client config), Cursor, Windsurf, VS Code, and any
other MCP client that supports custom headers. It will NOT appear as a
one-click "Add connector" inside claude.ai's own UI, which specifically
requires OAuth 2.1 -- that's a separate, much bigger subsystem, not built here.
"""

import contextvars
import functools
import logging
import time

import openai
from fastapi import HTTPException, status
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from app.auth.api_key import ApiKeyScope, InsufficientScope, InvalidApiKey, RateLimitExceeded, resolve_api_key_org
from app.db.pg import org_scoped_cursor
from app.routers.prompts import _get_org_prompt_row_or_404, _prompts_to_dicts, _search_filter_clause
from app.schemas.prompt import prompt_to_dict
from app.services import department_service, tag_service
from app.services.analytics_service import log_generation_event
from app.services.openai_service import generate_prompt as _generate_prompt_service

logger = logging.getLogger("truprompt.mcp")

mcp = FastMCP("truprompt", streamable_http_path="/")

_api_key_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("mcp_api_key", default=None)


class ApiKeyAuthMiddleware:
    """Reads the Authorization header off the raw ASGI scope and stashes the
    plaintext key in a contextvar -- resolved lazily per tool call (see
    _current_org_id) rather than here, so a missing/invalid key surfaces as a
    normal MCP tool error instead of failing the transport-level handshake."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        plaintext_key = (
            auth_header[len("Bearer ") :].strip()
            if auth_header.lower().startswith("bearer ")
            else None
        )

        token = _api_key_var.set(plaintext_key)
        try:
            await self.app(scope, receive, send)
        finally:
            _api_key_var.reset(token)


def _current_org_id(required_scope: ApiKeyScope | None = None) -> str:
    """Resolves the calling org_id from the contextvar set by the middleware
    above. Mirrors app/auth/api_key.py's get_api_key_org, just for a transport
    that has no FastAPI Request/Depends to hang the resolution off of."""
    try:
        return resolve_api_key_org(_api_key_var.get(), required_scope)
    except InvalidApiKey as exc:
        raise ToolError(f"unauthorized: {exc}")
    except InsufficientScope as exc:
        raise ToolError(f"insufficient_scope: {exc}")
    except RateLimitExceeded as exc:
        raise ToolError(f"rate_limited: retry after {exc.retry_after}s")


def _get_prompt_row_or_tool_error(cur, prompt_id: str) -> dict:
    try:
        return _get_org_prompt_row_or_404(cur, prompt_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise ToolError("not_found") from exc
        raise ToolError("internal_error") from exc


def _logged_tool(func):
    """One logging.info per tool call (api key prefix, tool name, duration,
    success/failure) -- no new observability dependency. Also the single place
    that converts any unexpected exception into a generic ToolError so nothing
    leaks internal detail to the client."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        key_prefix = (_api_key_var.get() or "")[:12]
        try:
            result = func(*args, **kwargs)
        except ToolError as exc:
            logger.info(
                "mcp tool=%s key=%s duration_ms=%d ok=False error=%s",
                func.__name__, key_prefix, (time.monotonic() - start) * 1000, exc,
            )
            raise
        except Exception as exc:
            logger.exception(
                "mcp tool=%s key=%s duration_ms=%d ok=False unexpected_error",
                func.__name__, key_prefix, (time.monotonic() - start) * 1000,
            )
            raise ToolError("internal_error") from exc
        else:
            logger.info(
                "mcp tool=%s key=%s duration_ms=%d ok=True",
                func.__name__, key_prefix, (time.monotonic() - start) * 1000,
            )
            return result

    return wrapper


@mcp.tool()
@_logged_tool
def list_prompts(
    search: str | None = None,
    department_id: str | None = None,
    tag_id: str | None = None,
    status: str | None = None,
) -> dict:
    """List the calling org's saved prompts, optionally filtered by free-text
    search, department, tag, or status -- same filters as the app's own prompt
    list. Defaults to the org's approved, curated library (status="all" shows
    everything, including drafts)."""
    org_id = _current_org_id(ApiKeyScope.READ)
    extra_sql, extra_params = _search_filter_clause(search, department_id, tag_id, status or "approved")
    with org_scoped_cursor(org_id) as cur:
        cur.execute(f"select * from prompts where true{extra_sql} order by updated_at desc", extra_params)
        rows = cur.fetchall()
    return {"prompts": _prompts_to_dicts(org_id, rows)}


@mcp.tool()
@_logged_tool
def get_prompt(prompt_id: str) -> dict:
    """Get one saved prompt by id, including its custom fields and tags."""
    org_id = _current_org_id(ApiKeyScope.READ)
    with org_scoped_cursor(org_id) as cur:
        row = _get_prompt_row_or_tool_error(cur, prompt_id)
    return {"prompt": prompt_to_dict(row)}


@mcp.tool()
@_logged_tool
def generate_prompt(prompt_id: str) -> dict:
    """Regenerate a fresh AI-crafted prompt for one of the org's saved prompts.
    Read-only -- does not overwrite the stored prompt (same as the app's own
    "regenerate" button and the public REST API's /v1/prompts/{id}/generate)."""
    org_id = _current_org_id(ApiKeyScope.GENERATE)
    with org_scoped_cursor(org_id) as cur:
        row = _get_prompt_row_or_tool_error(cur, prompt_id)

    if row["status"] == "archived":
        raise ToolError("archived: this prompt is retired and can no longer be generated from")

    try:
        result = _generate_prompt_service(row["user_prompt"], row["category"].split(", "))
    except openai.RateLimitError:
        raise ToolError("rate_limited")
    except openai.APIError:
        raise ToolError("upstream_error")

    log_generation_event(org_id, None, prompt_id, "mcp", result.get("modelUsed"))
    return {"optimizer": result["optimizer"], "prompt": result["prompt"]}


@mcp.tool()
@_logged_tool
def list_tags() -> dict:
    """List the calling org's tags."""
    org_id = _current_org_id(ApiKeyScope.READ)
    rows = tag_service.list_tags(org_id)
    return {"tags": [{"id": r["id"], "name": r["name"]} for r in rows]}


@mcp.tool()
@_logged_tool
def list_departments() -> dict:
    """List the calling org's departments."""
    org_id = _current_org_id(ApiKeyScope.READ)
    rows = department_service.list_departments(org_id)
    return {"departments": [{"id": r["id"], "name": r["name"]} for r in rows]}


mcp_app = mcp.streamable_http_app()
mcp_app.add_middleware(ApiKeyAuthMiddleware)
