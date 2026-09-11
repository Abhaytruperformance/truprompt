"""Invariant: a key's request budget is enforced through the real HTTP path
-- asserting the actual 429 + Retry-After response, not calling the private
_check_rate_limit helper directly (that would test the implementation, not
the behavior callers actually depend on)."""

from app.core.config import settings


def test_exceeding_the_limit_returns_429_with_retry_after(test_client, seed_prompt, seed_api_key, org_a, mock_llm, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY_RATE_LIMIT_PER_MINUTE", 2)
    prompt = seed_prompt()
    _row, plaintext_key = seed_api_key(org_a["org_id"], org_a["owner"]["id"])
    headers = {"Authorization": f"Bearer {plaintext_key}"}

    r1 = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers=headers)
    r2 = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers=headers)
    r3 = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert "retry-after" in {k.lower() for k in r3.headers.keys()}
