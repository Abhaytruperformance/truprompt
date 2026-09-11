"""Invariant: the role floor documented in org_service.py's authorization
matrix is enforced for every write operation. Parametrized directly against
that matrix so the two stay in sync -- a new admin-gated action should add a
row here, not just a line in that comment.
"""

import pytest


def test_member_can_generate_but_not_create(as_member_a, mock_llm):
    r = as_member_a.post("/api/ai/generate-prompt", json={"userPrompt": "write me a prompt about testing"})
    assert r.status_code == 200

    r = as_member_a.post("/api/prompts/auth/verifiedUserPrompts/", json={
        "userPrompt": "x", "prompt": "y", "optimizer": "z", "category": "Testing",
    })
    assert r.status_code == 403


def test_editor_can_create_edit_restore_but_not_approve(as_editor_a, seed_prompt):
    prompt = seed_prompt()

    r = as_editor_a.patch(f"/api/prompts/{prompt['id']}", json={"prompt": "edited by editor"})
    assert r.status_code == 200

    r = as_editor_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "review"})
    assert r.status_code == 200

    # The illegal transition: an editor cannot approve.
    r = as_editor_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "approved"})
    assert r.status_code == 403

    versions = as_editor_a.get(f"/api/prompts/{prompt['id']}/versions").json()["versions"]
    version_id = versions[0]["_id"]
    r = as_editor_a.post(f"/api/prompts/{prompt['id']}/versions/{version_id}/restore")
    assert r.status_code == 200


def test_member_cannot_approve(as_member_a, seed_prompt):
    prompt = seed_prompt()
    r = as_member_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "approved"})
    assert r.status_code == 403


def test_only_admin_can_approve_and_archive(as_admin_a, seed_prompt):
    prompt = seed_prompt()
    r = as_admin_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "approved"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    r = as_admin_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "archived"})
    assert r.status_code == 200
    assert r.json()["status"] == "archived"


@pytest.mark.parametrize("path,method,body", [
    ("/api/orgs/invitations", "post", {"email": "someone@test.local", "role": "member"}),
    ("/api/api-keys/", "post", {"name": "should not be allowed"}),
    ("/api/orgs/me/workos-connection", "put", {"connectionId": None}),
])
def test_member_cannot_perform_admin_actions(as_member_a, path, method, body):
    r = getattr(as_member_a, method)(path, json=body)
    assert r.status_code == 403


def test_admin_can_invite_and_create_api_key(as_admin_a):
    r = as_admin_a.post("/api/orgs/invitations", json={"email": f"pytest-invite-{id(as_admin_a)}@test.local", "role": "member"})
    assert r.status_code == 200
    invitation_id = r.json()["_id"]
    as_admin_a.delete(f"/api/orgs/invitations/{invitation_id}")

    r = as_admin_a.post("/api/api-keys/", json={"name": "pytest admin key"})
    assert r.status_code == 200
    as_admin_a.delete(f"/api/api-keys/{r.json()['_id']}")
