from app.db.pg import org_scoped_cursor


def list_tags(org_id: str) -> list[dict]:
    with org_scoped_cursor(org_id) as cur:
        cur.execute("select * from tags where org_id = %s order by name", (org_id,))
        return cur.fetchall()


def create_tag(org_id: str, name: str) -> dict:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "insert into tags (org_id, name) values (%s, %s) returning *",
            (org_id, name),
        )
        return cur.fetchone()


def delete_tag(org_id: str, tag_id: str) -> dict | None:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "delete from tags where id = %s and org_id = %s returning *",
            (tag_id, org_id),
        )
        return cur.fetchone()


def get_tags_for_prompts(org_id: str, prompt_ids: list[str]) -> dict[str, list[str]]:
    """Returns {prompt_id: [tag_id, ...]} for the given prompts, one batched query."""
    if not prompt_ids:
        return {}
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "select prompt_id, tag_id from prompt_tags where prompt_id = any(%s::uuid[])",
            (prompt_ids,),
        )
        rows = cur.fetchall()

    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row["prompt_id"], []).append(row["tag_id"])
    return result


def set_prompt_tags(org_id: str, prompt_id: str, tag_ids: list[str]) -> None:
    with org_scoped_cursor(org_id) as cur:
        cur.execute("delete from prompt_tags where prompt_id = %s", (prompt_id,))
        for tag_id in tag_ids:
            cur.execute(
                "insert into prompt_tags (prompt_id, tag_id, org_id) values (%s, %s, %s)",
                (prompt_id, tag_id, org_id),
            )
