"""Invariant: every governance action produces exactly one matching
audit_events row, and a logging failure never breaks the action it logs."""

from app.db.supabase import supabase
from app.services.audit_service import Action, ResourceType


def _latest_audit_row(resource_id: str, action: str):
    result = (
        supabase.table("audit_events")
        .select("*")
        .eq("resource_id", resource_id)
        .eq("action", action)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def test_approve_logs_an_audit_event(as_admin_a, seed_prompt):
    prompt = seed_prompt()
    as_admin_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "approved"})
    row = _latest_audit_row(prompt["id"], Action.PROMPT_APPROVED)
    assert row is not None
    assert row["resource_type"] == ResourceType.PROMPT


def test_archive_logs_an_audit_event(as_admin_a, seed_prompt):
    prompt = seed_prompt()
    as_admin_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "archived"})
    row = _latest_audit_row(prompt["id"], Action.PROMPT_ARCHIVED)
    assert row is not None


def test_api_key_create_and_revoke_log_audit_events(as_admin_a, org_a):
    r = as_admin_a.post("/api/api-keys/", json={"name": "pytest audit test"})
    key = r.json()
    assert _latest_audit_row(key["_id"], Action.API_KEY_CREATED) is not None

    as_admin_a.delete(f"/api/api-keys/{key['_id']}")
    assert _latest_audit_row(key["_id"], Action.API_KEY_REVOKED) is not None


def test_share_create_and_revoke_log_audit_events(as_editor_a, seed_prompt):
    prompt = seed_prompt()
    share = as_editor_a.post(f"/api/prompts/{prompt['id']}/share", json={"generationLimit": 5}).json()
    assert _latest_audit_row(share["_id"], Action.SHARE_CREATED) is not None

    as_editor_a.delete(f"/api/prompts/{prompt['id']}/share/{share['_id']}")
    assert _latest_audit_row(share["_id"], Action.SHARE_REVOKED) is not None


def test_role_change_logs_an_audit_event(as_admin_a, org_a):
    member_id = org_a["member"]["id"]
    as_admin_a.patch(f"/api/orgs/members/{member_id}", json={"role": "editor"})
    row = _latest_audit_row(member_id, Action.MEMBER_ROLE_CHANGED)
    assert row is not None
    assert row["metadata"]["to"] == "editor"

    # restore the fixture user's role -- session-scoped fixtures are
    # immutable by convention; undo this test's own mutation immediately.
    as_admin_a.patch(f"/api/orgs/members/{member_id}", json={"role": "member"})


def test_audit_write_failure_does_not_break_the_underlying_action(monkeypatch, as_admin_a, seed_prompt):
    import app.services.audit_service as audit_svc

    def broken_cursor(*args, **kwargs):
        raise RuntimeError("simulated audit-write failure")

    monkeypatch.setattr(audit_svc, "org_scoped_cursor", broken_cursor)

    prompt = seed_prompt()
    r = as_admin_a.patch(f"/api/prompts/{prompt['id']}/status", json={"status": "approved"})
    assert r.status_code == 200, "the approve action itself must still succeed even if audit logging is broken"
    assert r.json()["status"] == "approved"
