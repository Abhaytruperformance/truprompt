from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user, require_role
from app.core.config import settings
from app.db.pg import org_scoped_cursor
from app.schemas.custom_field import CustomFieldValuesUpdate
from app.schemas.prompt import PromptCreate, PromptStatusUpdate, PromptUpdate, RatingUpdate, prompt_to_dict
from app.schemas.share import ShareCreate, share_to_dict
from app.schemas.tag import PromptTagsUpdate
from app.schemas.version import version_to_dict
from app.services.analytics_service import get_ratings_for_prompts, set_prompt_rating
from app.services.audit_service import Action, ResourceType, log_audit_event
from app.services.custom_field_service import get_values_for_prompts, set_prompt_field_values
from app.services.org_service import ROLE_RANK
from app.services.share_service import create_share, list_shares, revoke_share
from app.services.tag_service import get_tags_for_prompts, set_prompt_tags
from app.services.version_service import get_version, list_versions, snapshot_version

router = APIRouter()


def _prompts_to_dicts(org_id: str, rows: list[dict], user_id: str | None = None) -> list[dict]:
    prompt_ids = [row["id"] for row in rows]
    values_by_prompt = get_values_for_prompts(org_id, prompt_ids)
    tags_by_prompt = get_tags_for_prompts(org_id, prompt_ids)
    ratings_by_prompt = get_ratings_for_prompts(org_id, prompt_ids, user_id)
    return [
        prompt_to_dict(
            row, values_by_prompt.get(row["id"]), tags_by_prompt.get(row["id"]), ratings_by_prompt.get(row["id"])
        )
        for row in rows
    ]


def _get_org_prompt_row_or_404(cur, prompt_id: str) -> dict:
    # org_id filtering happens via RLS (the session's app.org_id), not an
    # explicit WHERE clause here -- the policy already restricts what this
    # connection can see, so a row from another org simply won't come back.
    cur.execute("select * from prompts where id = %s limit 1", (prompt_id,))
    row = cur.fetchone()
    if not row:
        # Same 404 whether the id doesn't exist or belongs to another org --
        # never reveal that a prompt exists in a tenant the caller can't see.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return row


# NOTE: literal paths must be declared before the generic "/{prompt_id}" route below,
# otherwise FastAPI would match "auth" or "updatePromptCount" as a prompt_id.


def _search_filter_clause(
    search: str | None, department_id: str | None, tag_id: str | None, status: str | None = None
) -> tuple[str, list]:
    """Builds additional conditional WHERE clauses + params for prompt search/filter.

    `status="all"` is a sentinel, not a real DB value -- it means "skip status
    filtering entirely" (used by ManagePanel's admin view), distinct from
    omitting the param, which callers may default elsewhere (see get_all_prompts).
    """
    clauses = []
    params: list = []
    if search:
        clauses.append("(user_prompt ilike %s or prompt ilike %s)")
        like = f"%{search}%"
        params.extend([like, like])
    if department_id:
        clauses.append("department_id = %s")
        params.append(department_id)
    if tag_id:
        clauses.append("id in (select prompt_id from prompt_tags where tag_id = %s)")
        params.append(tag_id)
    if status and status != "all":
        clauses.append("status = %s")
        params.append(status)
    return ("".join(f" and {c}" for c in clauses), params)


@router.get("/auth/verifiedUserPrompts/")
def get_my_prompts(
    current_user: dict = Depends(get_current_user),
    search: str | None = None,
    departmentId: str | None = None,
    tagId: str | None = None,
    status: str | None = None,
):
    # No default status filter here -- this is a user's own list, they should
    # see everything they've written regardless of review state.
    extra_sql, extra_params = _search_filter_clause(search, departmentId, tagId, status)
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute(
            f"select * from prompts where user_id = %s{extra_sql} order by updated_at desc",
            (current_user["id"], *extra_params),
        )
        rows = cur.fetchall()
    return {"allPrompts": _prompts_to_dicts(current_user["org_id"], rows, current_user["id"])}


@router.post("/auth/verifiedUserPrompts/")
def create_prompt(body: PromptCreate, current_user: dict = Depends(require_role("editor"))):
    # Defense in depth, same reasoning as generate_prompt's own truncation --
    # a client could bypass the extraction endpoints and send an arbitrary-
    # length sourceContext straight here.
    source_context = body.sourceContext.strip()[: settings.MAX_CONTEXT_CHARS] if body.sourceContext else None

    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute(
            """insert into prompts (org_id, user_id, category, user_prompt, prompt, optimizer, department_id,
                                     source_type, source_name, source_context, status)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft') returning *""",
            (
                current_user["org_id"],
                current_user["id"],
                body.category,
                body.userPrompt,
                body.prompt,
                body.optimizer,
                body.departmentId,
                body.sourceType,
                body.sourceName,
                source_context,
            ),
        )
        row = cur.fetchone()
    return prompt_to_dict(row)


@router.patch("/updatePromptCount/{prompt_id}")
def update_prompt_count(prompt_id: str, current_user: dict = Depends(get_current_user)):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        row = _get_org_prompt_row_or_404(cur, prompt_id)
        cur.execute(
            """update prompts set most_used_prompt_count = %s, updated_at = now()
               where id = %s returning *""",
            (row["most_used_prompt_count"] + 1, prompt_id),
        )
        updated = cur.fetchone()
    return prompt_to_dict(updated)


@router.get("/")
def get_all_prompts(
    current_user: dict = Depends(get_current_user),
    search: str | None = None,
    departmentId: str | None = None,
    tagId: str | None = None,
    status: str | None = None,
):
    # Org-scoped "most used" library, not a global cross-tenant list -- this was
    # a public, unauthenticated endpoint before multi-tenancy existed, which
    # would otherwise leak every org's prompts to every other org.
    #
    # Defaults to approved-only -- this is the shared, curated library every
    # member browses, not a personal list, so unreviewed drafts stay out of it
    # unless explicitly asked for (status=all shows everything, for
    # ManagePanel's admin view; a specific status filters to just that).
    extra_sql, extra_params = _search_filter_clause(search, departmentId, tagId, status or "approved")
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        cur.execute(
            f"select * from prompts where true{extra_sql} order by most_used_prompt_count desc",
            extra_params,
        )
        rows = cur.fetchall()
    return {"allPrompts": _prompts_to_dicts(current_user["org_id"], rows, current_user["id"])}


@router.get("/{prompt_id}")
def get_single_prompt(prompt_id: str, current_user: dict = Depends(get_current_user)):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        row = _get_org_prompt_row_or_404(cur, prompt_id)
    values = get_values_for_prompts(current_user["org_id"], [row["id"]])
    tags = get_tags_for_prompts(current_user["org_id"], [row["id"]])
    ratings = get_ratings_for_prompts(current_user["org_id"], [row["id"]], current_user["id"])
    return {"prompt": prompt_to_dict(row, values.get(row["id"]), tags.get(row["id"]), ratings.get(row["id"]))}


@router.patch("/{prompt_id}")
def update_prompt(
    prompt_id: str, body: PromptUpdate, current_user: dict = Depends(require_role("editor"))
):
    # Editor+ in the org can edit any of the org's prompts (shared team library),
    # not just prompts they personally created.
    # NOTE: exclude_unset (not "is not None") so departmentId: null can
    # explicitly unassign a department -- a field the client omitted entirely
    # stays untouched, but one it sent as null is a real update.
    updates = body.model_dump(exclude_unset=True)

    field_map = {
        "category": "category",
        "userPrompt": "user_prompt",
        "prompt": "prompt",
        "optimizer": "optimizer",
        "departmentId": "department_id",
    }
    db_updates = {field_map[k]: v for k, v in updates.items() if k in field_map}

    # Only category/user_prompt/prompt/optimizer are tracked in prompt_versions
    # -- a department-only change has nothing meaningful to snapshot there.
    _CONTENT_FIELDS = {"category", "user_prompt", "prompt", "optimizer"}

    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        if not db_updates:
            return prompt_to_dict(_get_org_prompt_row_or_404(cur, prompt_id))

        current_row = _get_org_prompt_row_or_404(cur, prompt_id)  # 404 before attempting the update
        if _CONTENT_FIELDS & db_updates.keys():
            snapshot_version(cur, current_user["org_id"], prompt_id, current_row, current_user["id"])
            # An "Approved" label has to mean "the current content was
            # reviewed," not "was reviewed at some point in the past" --
            # editing an approved prompt's content un-approves it.
            if current_row["status"] == "approved":
                db_updates["status"] = "draft"
                db_updates["approved_at"] = None
                db_updates["approved_by"] = None
        set_clause = ", ".join(f"{col} = %s" for col in db_updates)
        cur.execute(
            f"update prompts set {set_clause}, updated_at = now() where id = %s returning *",
            (*db_updates.values(), prompt_id),
        )
        updated = cur.fetchone()
    return prompt_to_dict(updated)


@router.patch("/{prompt_id}/status")
def update_prompt_status(
    prompt_id: str, body: PromptStatusUpdate, current_user: dict = Depends(require_role("editor"))
):
    # Editor+ can move between draft/review (submit/withdraw); only admin+ can
    # approve or archive -- that's the actual review gate, letting any editor
    # self-approve would defeat the point of a curated library.
    if body.status in ("approved", "archived") and ROLE_RANK.get(current_user["role"], -1) < ROLE_RANK["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can approve or archive a prompt",
        )

    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        _get_org_prompt_row_or_404(cur, prompt_id)
        if body.status == "approved":
            cur.execute(
                """update prompts set status = %s, approved_at = now(), approved_by = %s, updated_at = now()
                   where id = %s returning *""",
                (body.status, current_user["id"], prompt_id),
            )
        else:
            # Explicit invariant: approved_at/approved_by are non-null if and
            # only if status == 'approved' -- including on archive. Archiving
            # an approved prompt clears them too, not just draft/review; the
            # historical "who approved this and when" isn't lost, it lives in
            # audit_events (prompt.approved) permanently, independent of
            # what the live row's fast-access fields currently show.
            cur.execute(
                """update prompts set status = %s, approved_at = null, approved_by = null, updated_at = now()
                   where id = %s returning *""",
                (body.status, prompt_id),
            )
        updated = cur.fetchone()
    if body.status in ("approved", "archived"):
        action = Action.PROMPT_APPROVED if body.status == "approved" else Action.PROMPT_ARCHIVED
        log_audit_event(current_user["org_id"], current_user["id"], action, ResourceType.PROMPT, prompt_id)
    return prompt_to_dict(updated)


@router.delete("/{prompt_id}")
def delete_prompt(prompt_id: str, current_user: dict = Depends(require_role("editor"))):
    # Same shared-library role model as update_prompt -- editor+ can delete
    # any of the org's prompts, not just ones they personally created.
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        _get_org_prompt_row_or_404(cur, prompt_id)
        cur.execute("delete from prompts where id = %s returning *", (prompt_id,))
        deleted = cur.fetchone()
    return prompt_to_dict(deleted)


@router.get("/{prompt_id}/versions")
def get_prompt_versions(prompt_id: str, current_user: dict = Depends(get_current_user)):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        _get_org_prompt_row_or_404(cur, prompt_id)
        rows = list_versions(cur, prompt_id)
    return {"versions": [version_to_dict(row) for row in rows]}


@router.post("/{prompt_id}/versions/{version_id}/restore")
def restore_prompt_version(
    prompt_id: str, version_id: str, current_user: dict = Depends(require_role("editor"))
):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        current_row = _get_org_prompt_row_or_404(cur, prompt_id)
        version = get_version(cur, prompt_id, version_id)
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

        # Restoring is itself non-lossy -- snapshot the current state before
        # overwriting it, same invariant as every other edit.
        snapshot_version(cur, current_user["org_id"], prompt_id, current_row, current_user["id"])

        # Restoring changes content exactly like a normal edit does -- an
        # approved prompt restored to older content must not stay "approved"
        # with unreviewed content, same rule update_prompt already applies.
        if current_row["status"] == "approved":
            cur.execute(
                """update prompts set category = %s, user_prompt = %s, prompt = %s, optimizer = %s,
                   status = 'draft', approved_at = null, approved_by = null, updated_at = now()
                   where id = %s returning *""",
                (version["category"], version["user_prompt"], version["prompt"], version["optimizer"], prompt_id),
            )
        else:
            cur.execute(
                """update prompts set category = %s, user_prompt = %s, prompt = %s, optimizer = %s,
                   updated_at = now() where id = %s returning *""",
                (version["category"], version["user_prompt"], version["prompt"], version["optimizer"], prompt_id),
            )
        updated = cur.fetchone()
    return prompt_to_dict(updated)


@router.post("/{prompt_id}/share")
def create_prompt_share(
    prompt_id: str, body: ShareCreate, current_user: dict = Depends(require_role("editor"))
):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        _get_org_prompt_row_or_404(cur, prompt_id)
    share = create_share(
        current_user["org_id"], prompt_id, current_user["id"], body.password, body.generationLimit
    )
    log_audit_event(current_user["org_id"], current_user["id"], Action.SHARE_CREATED, ResourceType.SHARE, share["id"], {"promptId": prompt_id})
    return share_to_dict(share)


@router.get("/{prompt_id}/share")
def list_prompt_shares(prompt_id: str, current_user: dict = Depends(get_current_user)):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        _get_org_prompt_row_or_404(cur, prompt_id)
    shares = list_shares(current_user["org_id"], prompt_id)
    return {"shares": [share_to_dict(row) for row in shares]}


@router.delete("/{prompt_id}/share/{share_id}")
def revoke_prompt_share(
    prompt_id: str, share_id: str, current_user: dict = Depends(require_role("editor"))
):
    share = revoke_share(current_user["org_id"], share_id)
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")
    log_audit_event(current_user["org_id"], current_user["id"], Action.SHARE_REVOKED, ResourceType.SHARE, share_id, {"promptId": prompt_id})
    return share_to_dict(share)


@router.put("/{prompt_id}/custom-fields")
def update_prompt_custom_fields(
    prompt_id: str,
    body: CustomFieldValuesUpdate,
    current_user: dict = Depends(require_role("editor")),
):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        row = _get_org_prompt_row_or_404(cur, prompt_id)
    set_prompt_field_values(current_user["org_id"], prompt_id, body.values)
    values = get_values_for_prompts(current_user["org_id"], [prompt_id])
    return prompt_to_dict(row, values.get(prompt_id))


@router.put("/{prompt_id}/tags")
def update_prompt_tags(
    prompt_id: str,
    body: PromptTagsUpdate,
    current_user: dict = Depends(require_role("editor")),
):
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        row = _get_org_prompt_row_or_404(cur, prompt_id)
    set_prompt_tags(current_user["org_id"], prompt_id, body.tagIds)
    tags = get_tags_for_prompts(current_user["org_id"], [prompt_id])
    return prompt_to_dict(row, tags=tags.get(prompt_id))


@router.put("/{prompt_id}/rating")
def update_prompt_rating(
    prompt_id: str, body: RatingUpdate, current_user: dict = Depends(get_current_user)
):
    # Rating is feedback, not an edit -- open to any org member, no editor+
    # gate (unlike content/status changes elsewhere in this file).
    with org_scoped_cursor(current_user["org_id"], current_user["id"]) as cur:
        row = _get_org_prompt_row_or_404(cur, prompt_id)
    set_prompt_rating(current_user["org_id"], prompt_id, current_user["id"], body.rating)
    ratings = get_ratings_for_prompts(current_user["org_id"], [prompt_id], current_user["id"])
    return prompt_to_dict(row, rating=ratings.get(prompt_id))
