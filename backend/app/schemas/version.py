def version_to_dict(row: dict) -> dict:
    return {
        "_id": row["id"],
        "promptId": row["prompt_id"],
        "versionNumber": row["version_number"],
        "category": row["category"],
        "userPrompt": row["user_prompt"],
        "prompt": row["prompt"],
        "optimizer": row["optimizer"],
        "editedBy": row["edited_by"],
        "createdAt": row["created_at"],
    }
