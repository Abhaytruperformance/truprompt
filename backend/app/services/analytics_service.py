"""Native usage + ratings analytics -- not a Langfuse integration (that needs
a real external account, same kind of human-only blocker WorkOS SSO hit in
this project). See PROJECT-PLAN.md's Phase 2 "Analytics" item and the
feature's plan for the reasoning.
"""

import logging

from app.db.pg import org_scoped_cursor

logger = logging.getLogger("truprompt.analytics")


def log_generation_event(
    org_id: str,
    user_id: str | None,
    prompt_id: str | None,
    source: str,
    model: str | None,
    prompt_version_number: int | None = None,
) -> None:
    """Best-effort, never raises -- a transient analytics-write failure must
    never turn an already-successful generation into a failed request."""
    try:
        with org_scoped_cursor(org_id, user_id) as cur:
            cur.execute(
                """insert into generation_events (org_id, user_id, prompt_id, source, model, prompt_version_number)
                   values (%s, %s, %s, %s, %s, %s)""",
                (org_id, user_id, prompt_id, source, model, prompt_version_number),
            )
    except Exception:
        logger.warning("failed to log generation event (org=%s source=%s)", org_id, source, exc_info=True)


def get_org_analytics(org_id: str) -> dict:
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "select count(*) as n from generation_events "
            "where org_id = %s and created_at >= now() - interval '30 days'",
            (org_id,),
        )
        total_generations = cur.fetchone()["n"]

        cur.execute(
            "select source, count(*) as n from generation_events "
            "where org_id = %s and created_at >= now() - interval '30 days' group by source",
            (org_id,),
        )
        by_source = {row["source"]: row["n"] for row in cur.fetchall()}

        cur.execute(
            "select date_trunc('day', created_at)::date as day, count(*) as n from generation_events "
            "where org_id = %s and created_at >= now() - interval '30 days' group by day order by day",
            (org_id,),
        )
        by_day = [{"date": row["day"].isoformat(), "count": row["n"]} for row in cur.fetchall()]

        cur.execute(
            "select model, count(*) as n from generation_events "
            "where org_id = %s and created_at >= now() - interval '30 days' and model is not null "
            "group by model order by n desc limit 1",
            (org_id,),
        )
        top_model_row = cur.fetchone()
        most_used_model = top_model_row["model"] if top_model_row else None

        # "Most copied" -- most_used_prompt_count increments on copy, not
        # generation (see PromptResults.jsx/Playground.jsx's copyToClipboard).
        # Named for what it actually measures, not relabeled as "usage".
        cur.execute(
            "select id, user_prompt, most_used_prompt_count from prompts "
            "where org_id = %s and most_used_prompt_count > 0 "
            "order by most_used_prompt_count desc limit 5",
            (org_id,),
        )
        most_copied = [
            {"id": row["id"], "userPrompt": row["user_prompt"], "count": row["most_used_prompt_count"]}
            for row in cur.fetchall()
        ]

        cur.execute(
            "select p.id, p.user_prompt, avg(r.rating) as avg_rating, count(r.rating) as rating_count "
            "from prompts p join prompt_ratings r on r.prompt_id = p.id "
            "where p.org_id = %s group by p.id, p.user_prompt "
            "order by avg_rating desc limit 5",
            (org_id,),
        )
        top_rated = [
            {
                "id": row["id"],
                "userPrompt": row["user_prompt"],
                "avgRating": round(float(row["avg_rating"]), 1),
                "ratingCount": row["rating_count"],
            }
            for row in cur.fetchall()
        ]

        cur.execute(
            "select count(*) as n from api_keys "
            "where org_id = %s and revoked_at is null and last_used_at >= now() - interval '7 days'",
            (org_id,),
        )
        active_api_keys = cur.fetchone()["n"]

    return {
        "totalGenerations": total_generations,
        "generationsBySource": by_source,
        "generationsByDay": by_day,
        "mostUsedModel": most_used_model,
        "mostCopiedPrompts": most_copied,
        "topRatedPrompts": top_rated,
        "activeApiKeys": active_api_keys,
    }


def set_prompt_rating(org_id: str, prompt_id: str, user_id: str, rating: int) -> dict:
    with org_scoped_cursor(org_id, user_id) as cur:
        cur.execute(
            """insert into prompt_ratings (org_id, prompt_id, user_id, rating)
               values (%s, %s, %s, %s)
               on conflict (prompt_id, user_id)
               do update set rating = excluded.rating, updated_at = now()
               returning *""",
            (org_id, prompt_id, user_id, rating),
        )
        return cur.fetchone()


def get_ratings_for_prompts(org_id: str, prompt_ids: list[str], user_id: str | None = None) -> dict[str, dict]:
    """Returns {prompt_id: {"avg": float, "count": int, "mine": int | None}},
    one batched query -- same shape as tag_service.get_tags_for_prompts."""
    if not prompt_ids:
        return {}
    with org_scoped_cursor(org_id) as cur:
        cur.execute(
            "select prompt_id, avg(rating) as avg_rating, count(*) as n from prompt_ratings "
            "where prompt_id = any(%s::uuid[]) group by prompt_id",
            (prompt_ids,),
        )
        aggregates = {
            row["prompt_id"]: {"avg": round(float(row["avg_rating"]), 1), "count": row["n"]}
            for row in cur.fetchall()
        }

        mine_by_prompt: dict[str, int] = {}
        if user_id:
            cur.execute(
                "select prompt_id, rating from prompt_ratings "
                "where prompt_id = any(%s::uuid[]) and user_id = %s",
                (prompt_ids, user_id),
            )
            mine_by_prompt = {row["prompt_id"]: row["rating"] for row in cur.fetchall()}

    return {
        prompt_id: {
            "avg": aggregates.get(prompt_id, {}).get("avg"),
            "count": aggregates.get(prompt_id, {}).get("count", 0),
            "mine": mine_by_prompt.get(prompt_id),
        }
        for prompt_id in prompt_ids
    }
