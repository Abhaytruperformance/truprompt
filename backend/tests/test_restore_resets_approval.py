"""Invariant: an approved prompt can never silently keep stale content.

Permanent regression test for the Pass-1 bug: restore_prompt_version was
missing the same un-approve logic update_prompt already had, so restoring
an old version onto an approved prompt left status="approved" with content
nobody had actually reviewed.
"""


def test_editing_an_approved_prompt_reverts_to_draft(as_admin_a, as_editor_a, seed_prompt):
    prompt = seed_prompt()
    as_admin_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "approved"})

    r = as_editor_a.patch(f"/api/prompts/{prompt['id']}", json={"prompt": "new content"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "draft"
    assert body["approvedAt"] is None
    assert body["approvedBy"] is None


def test_restoring_an_approved_prompt_reverts_to_draft(as_admin_a, as_editor_a, seed_prompt):
    prompt = seed_prompt()
    as_editor_a.patch(f"/api/prompts/{prompt['id']}", json={"prompt": "v2 content"})
    approved = as_admin_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "approved"}).json()
    assert approved["status"] == "approved"
    assert approved["approvedBy"] is not None
    assert approved["approvedAt"] is not None

    versions = as_editor_a.get(f"/api/prompts/{prompt['id']}/versions").json()["versions"]
    oldest_version_id = versions[-1]["_id"]

    restored = as_editor_a.post(f"/api/prompts/{prompt['id']}/versions/{oldest_version_id}/restore").json()
    assert restored["status"] == "draft", "the actual Pass-1 bug: restore must un-approve, same as an edit does"
    assert restored["approvedBy"] is None
    assert restored["approvedAt"] is None


def test_restore_snapshots_the_pre_restore_state_first(as_editor_a, seed_prompt):
    """Restoring is itself non-lossy -- confirms snapshot_version actually ran,
    not just that status changed."""
    prompt = seed_prompt()
    as_editor_a.patch(f"/api/prompts/{prompt['id']}", json={"prompt": "v2"})
    versions_before = as_editor_a.get(f"/api/prompts/{prompt['id']}/versions").json()["versions"]
    count_before = len(versions_before)

    as_editor_a.post(f"/api/prompts/{prompt['id']}/versions/{versions_before[0]['_id']}/restore")

    versions_after = as_editor_a.get(f"/api/prompts/{prompt['id']}/versions").json()["versions"]
    assert len(versions_after) == count_before + 1, "restore must snapshot the pre-restore content, not discard it"
