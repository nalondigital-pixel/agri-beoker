from app.db.supabase_client import supabase


def get_session(phone: str):
    response = (
        supabase.table("user_sessions")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def set_session(phone: str, current_step: str, temp_data: dict | None = None):
    response = (
        supabase.table("user_sessions")
        .upsert({
            "phone": phone,
            "current_step": current_step,
            "temp_data": temp_data or {},
        })
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def clear_session(phone: str):
    supabase.table("user_sessions").delete().eq("phone", phone).execute()