def snapshot_version(cur, org_id: str, prompt_id: str, current_row: dict, edited_by: str) -> None:
    """Inserts the *current* (pre-edit) content of a prompt into prompt_versions
    with the next version_number -- called right before an update/restore
    overwrites the live row, so nothing is ever silently lost."""
    cur.execute(
        "select coalesce(max(version_number), 0) + 1 as next from prompt_versions where prompt_id = %s",
        (prompt_id,),
    )
    next_version = cur.fetchone()["next"]
    cur.execute(
        """insert into prompt_versions
           (org_id, prompt_id, version_number, category, user_prompt, prompt, optimizer, edited_by)
           values (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            org_id,
            prompt_id,
            next_version,
            current_row["category"],
            current_row["user_prompt"],
            current_row["prompt"],
            current_row["optimizer"],
            edited_by,
        ),
    )


def current_version_number(cur, prompt_id: str) -> int:
    """The implicit version number of the prompt's *live* content -- one past
    the last snapshot, since prompt_versions only ever stores pre-edit
    states, never the current one. Used to tag generation_events with which
    version was live when a generation happened, without needing (or being
    able to create) an actual prompt_versions row for "right now"."""
    cur.execute(
        "select coalesce(max(version_number), 0) + 1 as next from prompt_versions where prompt_id = %s",
        (prompt_id,),
    )
    return cur.fetchone()["next"]


def list_versions(cur, prompt_id: str) -> list[dict]:
    cur.execute(
        "select * from prompt_versions where prompt_id = %s order by version_number desc",
        (prompt_id,),
    )
    return cur.fetchall()


def get_version(cur, prompt_id: str, version_id: str) -> dict | None:
    cur.execute(
        "select * from prompt_versions where id = %s and prompt_id = %s limit 1",
        (version_id, prompt_id),
    )
    return cur.fetchone()
