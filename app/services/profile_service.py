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

    if response.data:
        return response.data[0]

    return None


def create_profile(phone: str, data: dict | None = None):
    payload = data or {}
    payload["phone"] = phone

    response = (
        supabase.table("user_profiles")
        .upsert(payload, on_conflict="phone")
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def update_profile(phone: str, data: dict):
    data["phone"] = phone
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("user_profiles")
        .upsert(data, on_conflict="phone")
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def has_completed_registration(phone: str):
    profile = get_profile(phone)

    if not profile:
        return False

    has_name = bool(profile.get("name"))
    has_language = bool(profile.get("language"))
    has_city = bool(profile.get("city"))
    agreed_terms = profile.get("agreed_terms") is True

    return has_name and has_language and has_city and agreed_terms


def get_display_name(phone: str):
    profile = get_profile(phone)

    if profile and profile.get("name"):
        return profile.get("name")

    return phone


def calculate_trust_rank(trust_score: int):
    if trust_score >= 85:
        return "Trusted Seller"

    if trust_score >= 60:
        return "Reliable User"

    if trust_score >= 35:
        return "Growing User"

    return "New User"


def recalculate_trust(phone: str):
    profile = get_profile(phone)

    if not profile:
        return None

    successful_deals = profile.get("successful_deals") or 0
    total_matches = profile.get("total_matches_allocated") or 0
    ghost_match_strikes = profile.get("ghost_match_strikes") or 0
    verified = profile.get("verified") or False
    vouch_count = profile.get("vouch_count") or 0

    score = 25

    score += min(successful_deals * 10, 40)
    score += min(vouch_count * 5, 15)

    if verified:
        score += 15

    if total_matches > 0:
        completion_rate = successful_deals / total_matches
        score += int(completion_rate * 20)

    score -= ghost_match_strikes * 10

    if score < 0:
        score = 0

    if score > 100:
        score = 100

    trust_rank = calculate_trust_rank(score)

    return update_profile(phone, {
        "trust_score": score,
        "trust_rank": trust_rank,
    })


def reward_successful_deal(phone: str):
    profile = get_profile(phone)

    if not profile:
        return None

    successful_deals = profile.get("successful_deals") or 0
    daily_tokens = profile.get("daily_tokens") or 0

    update_profile(phone, {
        "successful_deals": successful_deals + 1,
        "daily_tokens": daily_tokens + 1,
    })

    return recalculate_trust(phone)


def increment_match_allocated(phone: str):
    profile = get_profile(phone)

    if not profile:
        return None

    total_matches = profile.get("total_matches_allocated") or 0

    update_profile(phone, {
        "total_matches_allocated": total_matches + 1,
    })

    return recalculate_trust(phone)


def update_last_active(phone: str):
    return update_profile(phone, {
        "last_active_at": datetime.now(timezone.utc).isoformat(),
    })