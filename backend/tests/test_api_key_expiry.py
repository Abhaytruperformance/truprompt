"""Invariant: an expired API key is always rejected -- adding the
expires_at column without enforcing it would be purely cosmetic."""

from datetime import datetime, timedelta, timezone

from app.db.supabase import supabase


def test_fresh_key_with_future_expiry_succeeds(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt()
    _row, plaintext_key = seed_api_key(org_a["org_id"], org_a["owner"]["id"], expires_in_days=1)
    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {plaintext_key}"})
    assert r.status_code == 200


def test_expired_key_is_rejected(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt()
    row, plaintext_key = seed_api_key(org_a["org_id"], org_a["owner"]["id"], expires_in_days=1)

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    supabase.table("api_keys").update({"expires_at": past}).eq("id", row["id"]).execute()

    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {plaintext_key}"})
    assert r.status_code == 401


def test_key_with_no_expiry_never_expires(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt()
    _row, plaintext_key = seed_api_key(org_a["org_id"], org_a["owner"]["id"], expires_in_days=None)
    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {plaintext_key}"})
    assert r.status_code == 200
