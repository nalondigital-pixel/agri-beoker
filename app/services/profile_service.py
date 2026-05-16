from app.db.supabase_client import supabase


def get_profile(phone: str):
    response = (
        supabase.table("user_profiles")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def create_or_update_profile(phone: str, data: dict):
    payload = {
        "phone": phone,
        **data,
    }

    response = (
        supabase.table("user_profiles")
        .upsert(payload)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def has_completed_registration(phone: str) -> bool:
    profile = get_profile(phone)

    if not profile:
        return False

    return bool(
        profile.get("language")
        and profile.get("role")
        and profile.get("city")
        and profile.get("agreed_terms") is True
    )