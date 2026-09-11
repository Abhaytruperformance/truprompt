"""Invariant: cross-org access is always 404, never a data leak.

RLS (org_scoped_cursor) is the real enforcement point -- these tests exercise
it through the actual HTTP surface, both auth paths (cookie session and API
key), rather than asserting anything about RLS policies directly.
"""


def test_cross_org_read_is_404_not_a_leak(as_editor_a, as_owner_b, seed_prompt, org_b):
    prompt = seed_prompt()
    r = as_owner_b.get(f"/api/prompts/{prompt['id']}")
    assert r.status_code == 404


def test_cross_org_edit_is_404(as_editor_a, as_owner_b, seed_prompt):
    prompt = seed_prompt()
    r = as_owner_b.patch(f"/api/prompts/{prompt['id']}", json={"prompt": "hijacked"})
    assert r.status_code == 404
    # and the content is provably untouched from Org A's own view
    r2 = as_editor_a.get(f"/api/prompts/{prompt['id']}")
    assert r2.json()["prompt"]["prompt"] == prompt["prompt"]


def test_cross_org_delete_is_404(as_owner_b, seed_prompt):
    prompt = seed_prompt()
    r = as_owner_b.delete(f"/api/prompts/{prompt['id']}")
    assert r.status_code == 404


def test_cross_org_restore_is_404(as_editor_a, as_owner_b, seed_prompt):
    prompt = seed_prompt()
    as_editor_a.patch(f"/api/prompts/{prompt['id']}", json={"prompt": "v2"})
    versions = as_editor_a.get(f"/api/prompts/{prompt['id']}/versions").json()["versions"]
    version_id = versions[0]["_id"]
    r = as_owner_b.post(f"/api/prompts/{prompt['id']}/versions/{version_id}/restore")
    assert r.status_code == 404


def test_api_key_cannot_reach_another_orgs_prompt(test_client, seed_prompt, seed_api_key, org_b, mock_llm):
    prompt = seed_prompt()
    _row, plaintext_key = seed_api_key(org_b["org_id"], org_b["owner"]["id"])
    r = test_client.post(f"/v1/prompts/{prompt['id']}/generate", headers={"Authorization": f"Bearer {plaintext_key}"})
    assert r.status_code == 404
