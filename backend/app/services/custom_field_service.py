import json

from app.db.pg import org_scoped_cursor


def list_field_defs(org_id: str) -> list[dict]:
    with org_scoped_cursor(org_id) as cur:
        cur.execute("select * from custom_field_defs where org_id = %s order by name", (org_id,))
        return cur.fetchall()


def create_field_def(org_id: str, name: str, field_type: str, options: list[str] | None) -> dict:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            """insert into custom_field_defs (org_id, name, field_type, options)
               values (%s, %s, %s, %s) returning *""",
            (org_id, name, field_type, json.dumps(options) if options else None),
        )
        return cur.fetchone()


def delete_field_def(org_id: str, field_def_id: str) -> dict | None:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "delete from custom_field_defs where id = %s and org_id = %s returning *",
            (field_def_id, org_id),
        )
        return cur.fetchone()


def get_values_for_prompts(org_id: str, prompt_ids: list[str]) -> dict[str, dict[str, str]]:
    """Returns {prompt_id: {field_def_id: value}} for the given prompts, one batched query."""
    if not prompt_ids:
        return {}
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "select prompt_id, field_def_id, value from prompt_custom_field_values "
            "where prompt_id = any(%s::uuid[])",
            (prompt_ids,),
        )
        rows = cur.fetchall()

    result: dict[str, dict[str, str]] = {}
    for row in rows:
        result.setdefault(row["prompt_id"], {})[row["field_def_id"]] = row["value"]
    return result


def set_prompt_field_values(org_id: str, prompt_id: str, values: dict[str, str]) -> None:
    with org_scoped_cursor(org_id) as cur:
        for field_def_id, value in values.items():
            cur.execute(
                """insert into prompt_custom_field_values (org_id, prompt_id, field_def_id, value)
                   values (%s, %s, %s, %s)
                   on conflict (prompt_id, field_def_id) do update set value = excluded.value""",
                (org_id, prompt_id, field_def_id, value),
            )
