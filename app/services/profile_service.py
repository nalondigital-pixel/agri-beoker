from datetime import datetime, timezone

from app.db.supabase_client import supabase


def get_profile(phone: str):
    response = (
        supabase.table("user_profiles")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
def update_profile(phone: str, data: dict):
    data["phone"] = phone

    response = (
        supabase.table("user_profiles")
        .upsert(data, on_conflict="phone")
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


    if response.data:
        return response.data[0]

    return None


def create_or_update_profile(phone: str, data: dict):
    payload = {
        "phone": phone,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    response = supabase.table("user_profiles").upsert(payload).execute()

    if response.data:
        return response.data[0]

    return None


def has_completed_registration(phone: str) -> bool:
    profile = get_profile(phone)

    if not profile:
        return False

    return bool(
        profile.get("name")
        and profile.get("language")
        and profile.get("role")
        and profile.get("city")
        and profile.get("agreed_terms") is True
    )


def get_display_name(phone: str):
    profile = get_profile(phone)

    if profile and profile.get("name"):
        return profile["name"]

    return phone


def calculate_trust_rank(score: int, successful_deals: int):
    if successful_deals >= 50 and score >= 85:
        return "Trusted Partner"

    if score >= 60:
        return "Verified Trader"

    return "New Seller"


def recalculate_trust(phone: str):
    profile = get_profile(phone)

    if not profile:
        return None

    base_score = 25 if profile.get("agreed_terms") else 0
    deal_score = min((profile.get("successful_deals") or 0) * 5, 50)
    vouch_score = min((profile.get("vouch_count") or 0) * 10, 25)

    trust_score = min(base_score + deal_score + vouch_score, 100)
    trust_rank = calculate_trust_rank(
        trust_score,
        profile.get("successful_deals") or 0,
    )

    return create_or_update_profile(phone, {
        "trust_score": trust_score,
        "trust_rank": trust_rank,
    })


def reward_successful_deal(phone: str):
    profile = get_profile(phone)

    if not profile:
        return None

    successful_deals = (profile.get("successful_deals") or 0) + 1
    daily_tokens = (profile.get("daily_tokens") or 3) + 1

    create_or_update_profile(phone, {
        "successful_deals": successful_deals,
        "daily_tokens": daily_tokens,
    })

    return recalculate_trust(phone)


def increment_match_allocated(phone: str):
    profile = get_profile(phone)

    if not profile:
        return None

    total = (profile.get("total_matches_allocated") or 0) + 1

    return create_or_update_profile(phone, {
        "total_matches_allocated": total,
    })