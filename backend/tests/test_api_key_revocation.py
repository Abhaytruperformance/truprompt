"""Invariant: a revoked API key is always rejected."""


def test_valid_key_succeeds(test_client, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt()
    _row, plaintext_key = seed_api_key(org_a["org_id"], org_a["owner"]["id"])
    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {plaintext_key}"})
    assert r.status_code == 200


def test_revoked_key_is_rejected(test_client, as_owner_a, seed_prompt, seed_api_key, org_a, mock_llm):
    prompt = seed_prompt()
    row, plaintext_key = seed_api_key(org_a["org_id"], org_a["owner"]["id"])

    r = as_owner_a.delete(f"/api/api-keys/{row['id']}")
    assert r.status_code == 200

    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {plaintext_key}"})
    assert r.status_code == 401
