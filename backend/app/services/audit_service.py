"""Audit log for admin/governance actions -- who did what, to what, when.
Separate from generation_events (that's usage, this is administration).

Limitation: actor_user_id assumes a human admin performed the action --
every current call site is a user-authenticated router. If a non-user actor
(an API key, MCP, a future background job) ever needs to perform an audited
action, this will need actor_type/actor_id instead of a bare user FK.

metadata must never contain: API keys/tokens, share passwords (hashed or
not), full prompt content, session cookies, or auth headers -- identifiers
and state transitions only (e.g. {"from": "member", "to": "admin"}).
"""

import json
import logging

from app.db.pg import org_scoped_cursor

logger = logging.getLogger("truprompt.audit")


# Constants, not scattered string literals -- keeps action/resource_type
# names from drifting ("prompt.approved" vs "prompt.approve" vs
# "prompts.approved") as more call sites get added.
class Action:
    PROMPT_APPROVED = "prompt.approved"
    PROMPT_ARCHIVED = "prompt.archived"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    MEMBER_ROLE_CHANGED = "member.role_changed"
    SHARE_CREATED = "share.created"
    SHARE_REVOKED = "share.revoked"
    SSO_CONNECTION_CHANGED = "sso.connection_changed"


class ResourceType:
    PROMPT = "prompt"
    API_KEY = "api_key"
    MEMBER = "member"
    SHARE = "share"
    ORGANIZATION = "organization"


def log_audit_event(
    org_id: str,
    actor_user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    metadata: dict | None = None,
) -> None:
    """Best-effort, never raises -- an audit-write failure must never break
    the action it's logging, same precedent as log_generation_event."""
    try:
        with org_scoped_cursor(org_id, actor_user_id) as cur:
            cur.execute(
                """insert into audit_events (org_id, actor_user_id, action, resource_type, resource_id, metadata)
                   values (%s, %s, %s, %s, %s, %s)""",
                (org_id, actor_user_id, action, resource_type, resource_id, json.dumps(metadata) if metadata else None),
            )
    except Exception:
        logger.warning("failed to log audit event (org=%s action=%s)", org_id, action, exc_info=True)
