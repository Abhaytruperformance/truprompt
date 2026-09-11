"""Shared pytest fixtures for the invariant suite.

"Things we never break" -- one place to read them, each pointing at its
actual test (see Pass 2 plan for the reasoning behind this list existing
here instead of a duplicated test file):

  - Cross-org access is always 404, never a data leak         -> test_tenant_isolation.py
  - Role floor is enforced for every write operation            -> test_authorization.py
  - An approved prompt can never silently keep stale content    -> test_restore_resets_approval.py
  - Revoked/expired API keys are always rejected                -> test_api_key_revocation.py, test_api_key_expiry.py
  - A share's generation limit can never be exceeded by a race  -> test_share_quota.py
  - SSRF: no private/loopback/link-local address is ever fetched -> test_content_ssrf.py
  - MCP tools respect the same org boundary as the REST API     -> test_mcp_isolation.py

Runs against the real dev Supabase DB (no separate test project exists yet --
see the Pass 2 plan for why, and what closes most of the real risk without
one). Session-scoped fixtures (the two test orgs + their role-seeded users)
are immutable by convention: no test may change a fixture user's role or
org membership. Everything else (prompts, shares, API keys) is function-
scoped, created and deleted by each test via the seed_* fixtures below.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.security import COOKIE_NAME, create_access_token
from app.db.supabase import supabase
from app.main import app
from app.services.org_service import create_org_for_user
from app.auth.microsoft import upsert_user_from_profile

_RUN_ID = uuid.uuid4().hex[:8]


def _make_user(label: str) -> dict:
    oid = f"pytest-{label}-{uuid.uuid4().hex}"
    return upsert_user_from_profile({
        "id": oid,
        "displayName": f"pytest-{_RUN_ID}-{label}",
        "mail": f"pytest-{_RUN_ID}-{label}@test.local",
    })


def _add_member(org_id: str, user_id: str, role: str) -> None:
    supabase.table("organization_members").insert(
        {"org_id": org_id, "user_id": user_id, "role": role}
    ).execute()


def _delete_org(org_id: str, user_ids: list[str] | None = None) -> None:
    # Cascades cover members/prompts/shares/keys/etc. -- safe for the final
    # session-level teardown of a whole fixture org, not used for individual
    # business-data cleanup during a test (that's explicit delete-by-id).
    # users.last_active_org_id has no cascade/set-null on this FK, so it has
    # to be cleared before the org can be deleted, or this fails with
    # "violates foreign key constraint users_last_active_org_id_fkey".
    supabase.table("users").update({"last_active_org_id": None}).eq("last_active_org_id", org_id).execute()
    supabase.table("organizations").delete().eq("id", org_id).execute()
    for uid in user_ids or []:
        supabase.table("users").delete().eq("id", uid).execute()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_stale_pytest_orgs():
    """Self-healing: if a previous run crashed mid-teardown, its orgs don't
    accumulate forever -- anything pytest-prefixed and older than a day gets
    swept before this run creates its own."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    stale = (
        supabase.table("organizations")
        .select("id,name")
        .like("name", "pytest-%")
        .lt("created_at", cutoff)
        .execute()
    )
    for row in stale.data or []:
        _delete_org(row["id"])
    yield


@pytest.fixture(scope="session")
def test_client():
    # Context-managed so the app's lifespan actually runs (required for the
    # mounted MCP sub-app's session manager -- see app/main.py's combined
    # lifespan, and the "Task group is not initialized" bug it fixed earlier
    # this project). One shared instance for the whole session; per-request
    # auth is via an explicit cookies= kwarg, not shared client-side state.
    with TestClient(app) as c:
        yield c


class ActingClient:
    """Thin wrapper around the shared TestClient that injects one user's auth
    cookie per request, without separate TestClient instances (which would
    each try to run their own app lifespan) or shared mutable cookie state
    (which would let one test's "acting as" bleed into another's)."""

    def __init__(self, client: TestClient, user_id: str, org_id: str):
        self._client = client
        self._cookies = {COOKIE_NAME: create_access_token(user_id, org_id)}
        self.user_id = user_id
        self.org_id = org_id

    def __getattr__(self, name):
        method = getattr(self._client, name)

        def wrapped(*args, **kwargs):
            kwargs.setdefault("cookies", self._cookies)
            return method(*args, **kwargs)

        return wrapped


@pytest.fixture(scope="session")
def org_a(test_client):
    """Org A: has one user seeded at each role. The primary org most tests
    act within; Org B (below) exists purely to prove isolation against it."""
    owner = _make_user("orgA-owner")
    org = create_org_for_user(owner)
    org["name"]  # sanity: real row
    member = _make_user("orgA-member")
    editor = _make_user("orgA-editor")
    admin = _make_user("orgA-admin")
    _add_member(org["id"], member["id"], "member")
    _add_member(org["id"], editor["id"], "editor")
    _add_member(org["id"], admin["id"], "admin")

    yield {
        "org_id": org["id"],
        "owner": owner,
        "admin": admin,
        "editor": editor,
        "member": member,
    }
    _delete_org(org["id"], [owner["id"], admin["id"], editor["id"], member["id"]])


@pytest.fixture(scope="session")
def org_b(test_client):
    """Org B: exists only to prove Org A can't reach into it. One owner is
    enough -- no test acts as a role-specific user inside Org B."""
    owner = _make_user("orgB-owner")
    org = create_org_for_user(owner)
    yield {"org_id": org["id"], "owner": owner}
    _delete_org(org["id"], [owner["id"]])


@pytest.fixture
def as_owner_a(test_client, org_a):
    return ActingClient(test_client, org_a["owner"]["id"], org_a["org_id"])


@pytest.fixture
def as_admin_a(test_client, org_a):
    return ActingClient(test_client, org_a["admin"]["id"], org_a["org_id"])


@pytest.fixture
def as_editor_a(test_client, org_a):
    return ActingClient(test_client, org_a["editor"]["id"], org_a["org_id"])


@pytest.fixture
def as_member_a(test_client, org_a):
    return ActingClient(test_client, org_a["member"]["id"], org_a["org_id"])


@pytest.fixture
def as_owner_b(test_client, org_b):
    return ActingClient(test_client, org_b["owner"]["id"], org_b["org_id"])


@pytest.fixture
def seed_prompt(org_a):
    """Function-scoped: every test gets its own prompt, deleted by id in
    teardown -- never relies on org-cascade for business data."""
    created_ids = []

    def _make(**overrides):
        row = {
            "org_id": org_a["org_id"],
            "user_id": org_a["editor"]["id"],
            "category": "Testing",
            "user_prompt": "pytest fixture prompt",
            "prompt": "fixture prompt content",
            "optimizer": "fixture optimizer",
            "status": "draft",
            **overrides,
        }
        result = supabase.table("prompts").insert(row).execute()
        prompt = result.data[0]
        created_ids.append(prompt["id"])
        return prompt

    yield _make
    for pid in created_ids:
        supabase.table("prompts").delete().eq("id", pid).execute()


@pytest.fixture
def seed_share():
    created_ids = []

    def _make(prompt_id: str, org_id: str, created_by: str, **overrides):
        row = {
            "org_id": org_id,
            "prompt_id": prompt_id,
            "token": f"pytest-{uuid.uuid4().hex}",
            "created_by": created_by,
            "generation_limit": None,
            "generation_count": 0,
            **overrides,
        }
        result = supabase.table("prompt_shares").insert(row).execute()
        share = result.data[0]
        created_ids.append(share["id"])
        return share

    yield _make
    for sid in created_ids:
        supabase.table("prompt_shares").delete().eq("id", sid).execute()


@pytest.fixture
def seed_api_key():
    from app.services.api_key_service import create_api_key

    created_ids = []

    def _make(org_id: str, created_by: str, name: str = "pytest key", expires_in_days=None, scopes=None):
        row, plaintext = create_api_key(org_id, name, created_by, expires_in_days, scopes)
        created_ids.append(row["id"])
        return row, plaintext

    yield _make
    for kid in created_ids:
        supabase.table("api_keys").delete().eq("id", kid).execute()


@pytest.fixture
def mock_llm(monkeypatch):
    """Patches the one seam every test in this suite that needs a fake LLM
    response uses: app.services.openai_service._client.chat.completions.create.
    Not anything deeper in the OpenAI SDK, so this survives internal
    refactors that don't change that call site."""
    import app.services.openai_service as svc

    class FakeUsage:
        prompt_tokens = 10
        completion_tokens = 5
        total_tokens = 15

    class FakeMessage:
        content = '{"optimizer": "fake optimizer", "prompt": "fake prompt"}'

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletion:
        choices = [FakeChoice()]
        usage = FakeUsage()

    calls = []

    class FakeCompletions:
        def create(self, model, messages, temperature):
            calls.append(model)
            return FakeCompletion()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(svc, "_client", FakeClient())
    return calls
