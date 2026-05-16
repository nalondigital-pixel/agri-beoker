from app.db.supabase_client import supabase


def is_blocked_user(phone: str) -> bool:
    if not phone:
        return False

    response = (
        supabase.table("blocked_users")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )

    return bool(response.data)


def block_user(phone: str, reason: str):
    response = (
        supabase.table("blocked_users")
        .upsert({
            "phone": phone,
            "reason": reason,
        })
        .execute()
    )

    return response.data