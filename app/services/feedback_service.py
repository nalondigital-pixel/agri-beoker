from datetime import datetime, timedelta, timezone

from app.db.supabase_client import supabase
from app.services.session_service import get_session, set_session, clear_session
from app.services.profile_service import reward_successful_deal
from app.services.language_service import translate


def schedule_deal_feedback(deal_id: str):
    due_at = datetime.now(timezone.utc) + timedelta(hours=24)

    response = (
        supabase.table("deals")
        .update({
            "feedback_due_at": due_at.isoformat(),
            "feedback_sent": False,
        })
        .eq("id", deal_id)
        .execute()
    )

    return response.data


def start_feedback_session(phone: str, deal_id: str, role: str):
    set_session(phone, "deal_feedback", {
        "deal_id": deal_id,
        "role": role,
    })


def get_deal(deal_id: str):
    response = (
        supabase.table("deals")
        .select("*")
        .eq("id", deal_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def create_untrusted_case(deal_id, reporter_phone, reported_phone, reason):
    response = (
        supabase.table("untrusted_queue")
        .insert({
            "deal_id": deal_id,
            "reporter_phone": reporter_phone,
            "reported_phone": reported_phone,
            "reason": reason,
            "status": "open",
        })
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def handle_feedback_response(phone: str, message: str):
    session = get_session(phone)

    if not session or session.get("current_step") != "deal_feedback":
        return None

    temp_data = session.get("temp_data") or {}
    deal_id = temp_data.get("deal_id")
    role = temp_data.get("role")

    if message.strip() not in ["1", "2"]:
        return {
            "handled": True,
            "reply": translate(phone, "feedback_invalid"),
        }

    deal = get_deal(deal_id)

    if not deal:
        clear_session(phone)
        return {
            "handled": True,
            "reply": translate(phone, "feedback_deal_not_found"),
        }

    now = datetime.now(timezone.utc).isoformat()

    if role == "buyer":
        feedback_field = "buyer_feedback"
        feedback_time_field = "buyer_feedback_at"
        other_phone = deal.get("seller_phone")
    else:
        feedback_field = "seller_feedback"
        feedback_time_field = "seller_feedback_at"
        other_phone = deal.get("buyer_phone")

    if message.strip() == "1":
        supabase.table("deals").update({
            feedback_field: "successful",
            feedback_time_field: now,
        }).eq("id", deal_id).execute()

        reward_successful_deal(phone)

        if other_phone:
            reward_successful_deal(other_phone)

        clear_session(phone)

        return {
            "handled": True,
            "reply": translate(phone, "feedback_success"),
        }

    if message.strip() == "2":
        supabase.table("deals").update({
            feedback_field: "flake_reported",
            feedback_time_field: now,
        }).eq("id", deal_id).execute()

        create_untrusted_case(
            deal_id=deal_id,
            reporter_phone=phone,
            reported_phone=other_phone,
            reason="User reported that the other person did not come.",
        )

        clear_session(phone)

        return {
            "handled": True,
            "reply": translate(phone, "feedback_reported"),
        }