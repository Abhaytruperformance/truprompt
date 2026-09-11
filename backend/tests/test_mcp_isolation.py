"""Invariant: MCP tools respect the same org boundary as the REST API.

Calls the real tool functions directly rather than speaking the full MCP
Streamable-HTTP/JSON-RPC protocol by hand (fragile to hand-roll correctly,
and the transport layer isn't the security boundary here anyway -- it's
already proven working over real HTTP earlier this session). This exercises
the actual security-relevant path: the middleware's contextvar -> resolve_api_key_org
-> org_scoped_cursor chain that every tool call goes through, using the exact
same contextvar the real ASGI middleware sets.
"""

from app.mcp_server import _api_key_var, list_prompts


def _call_as(plaintext_key: str, fn, *args, **kwargs):
    token = _api_key_var.set(plaintext_key)
    try:
        return fn(*args, **kwargs)
    finally:
        _api_key_var.reset(token)


def test_list_prompts_never_returns_another_orgs_prompt(seed_prompt, seed_api_key, org_a, org_b):
    prompt_a = seed_prompt(status="approved")
    _row_b, key_b = seed_api_key(org_b["org_id"], org_b["owner"]["id"])

    result = _call_as(key_b, list_prompts)
    ids = {p["_id"] for p in result["prompts"]}
    assert prompt_a["id"] not in ids


def test_list_prompts_returns_the_calling_orgs_own_prompt(seed_prompt, seed_api_key, org_a):
    prompt = seed_prompt(status="approved")
    _row, key_a = seed_api_key(org_a["org_id"], org_a["owner"]["id"])

    result = _call_as(key_a, list_prompts)
    ids = {p["_id"] for p in result["prompts"]}
    assert prompt["id"] in ids
