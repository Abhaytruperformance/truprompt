"""Invariant: an API key only has the capabilities its scopes explicitly
grant, enforced identically across REST and MCP -- both transports funnel
through the same resolve_api_key_org check."""

import pytest

from app.auth.api_key import ApiKeyScope
from app.db.supabase import supabase
from app.mcp_server import _api_key_var, generate_prompt, get_prompt, list_departments, list_prompts, list_tags
from mcp.server.fastmcp.exceptions import ToolError


def _call_mcp_as(plaintext_key, fn, *args, **kwargs):
    token = _api_key_var.set(plaintext_key)
    try:
        return fn(*args, **kwargs)
    finally:
        _api_key_var.reset(token)


def test_read_only_key_succeeds_on_all_read_tools(seed_prompt, seed_api_key, org_a):
    prompt = seed_prompt(status="approved")
    _row, key = seed_api_key(org_a["org_id"], org_a["owner"]["id"], scopes=[ApiKeyScope.READ])

    assert prompt["id"] in {p["_id"] for p in _call_mcp_as(key, list_prompts)["prompts"]}
    assert _call_mcp_as(key, get_prompt, prompt["id"])["prompt"]["_id"] == prompt["id"]
    _call_mcp_as(key, list_tags)  # must not raise
    _call_mcp_as(key, list_departments)  # must not raise


def test_read_only_key_is_denied_generate_on_both_transports(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt(status="approved")
    _row, key = seed_api_key(org_a["org_id"], org_a["owner"]["id"], scopes=[ApiKeyScope.READ])

    with pytest.raises(ToolError, match="insufficient_scope"):
        _call_mcp_as(key, generate_prompt, prompt["id"])

    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 403
    assert "prompts:generate" in r.json()["detail"]


def test_generate_only_key_succeeds_on_generate_but_not_read(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt(status="approved")
    _row, key = seed_api_key(org_a["org_id"], org_a["owner"]["id"], scopes=[ApiKeyScope.GENERATE])

    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200

    with pytest.raises(ToolError, match="insufficient_scope"):
        _call_mcp_as(key, list_prompts)
    with pytest.raises(ToolError, match="insufficient_scope"):
        _call_mcp_as(key, get_prompt, prompt["id"])
    with pytest.raises(ToolError, match="insufficient_scope"):
        _call_mcp_as(key, list_tags)
    with pytest.raises(ToolError, match="insufficient_scope"):
        _call_mcp_as(key, list_departments)


def test_empty_scopes_key_is_denied_everything(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt(status="approved")
    _row, key = seed_api_key(org_a["org_id"], org_a["owner"]["id"], scopes=[])

    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 403
    with pytest.raises(ToolError, match="insufficient_scope"):
        _call_mcp_as(key, list_prompts)


def test_legacy_null_scopes_key_succeeds_on_everything(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    """A key created before scopes existed (scopes=NULL on the row) must
    keep working exactly as it did before this feature shipped."""
    prompt = seed_prompt(status="approved")
    row, key = seed_api_key(org_a["org_id"], org_a["owner"]["id"])
    supabase.table("api_keys").update({"scopes": None}).eq("id", row["id"]).execute()

    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200
    _call_mcp_as(key, list_prompts)  # must not raise
