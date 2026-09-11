"""Invariant: an explicitly wrong model is rejected with a clear 400 before
any provider call is ever made -- never silently swapped for the default."""


def test_invalid_model_is_rejected_before_any_provider_call(as_editor_a, mock_llm):
    r = as_editor_a.post("/api/ai/generate-prompt", json={
        "userPrompt": "write me a prompt", "model": "not-a-real-model/definitely-fake",
    })
    assert r.status_code == 400
    assert mock_llm == [], "an invalid model must fail before the provider is ever called"


def test_omitted_model_still_succeeds_via_the_default(as_editor_a, mock_llm):
    r = as_editor_a.post("/api/ai/generate-prompt", json={"userPrompt": "write me a prompt"})
    assert r.status_code == 200
    assert len(mock_llm) == 1
