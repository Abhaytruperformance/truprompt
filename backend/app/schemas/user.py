def user_to_dict(row: dict) -> dict:
    """Maps a Supabase `users` row to the camelCase shape the frontend expects."""
    return {
        "_id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "profileImage": row["profile_image"],
    }
