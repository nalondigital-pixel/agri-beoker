from datetime import datetime, timedelta, timezone

from app.db.supabase_client import supabase
from app.services.session_service import get_session, set_session, clear_session
from app.services.profile_service import reward_successful_deal
from app.services.language_service import translate


def schedule_deal_feedback(deal_id):
    feedback_due_at = datetime.now(timezone.utc) + timedelta(hours=24)

    response = (
        supabase.table("deals")
        .update({
            "feedback_due_at": feedback_due_at.isoformat(),
            "feedback_sent": False,
        })
        .eq("id", deal_id)
        .execute()
    )

    return response.data


def get_deal(deal_id):
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


def start_feedback_session(phone: str, deal_id, role: str):
    set_session(
        phone,
        "deal_feedback",
        {
            "deal_id": deal_id,
            "role": role,
        },
    )


def create_untrusted_case(deal, reporter_phone: str, reported_phone: str, reason: str):
    response = supabase.table("untrusted_queue").insert({
        "deal_id": deal.get("id"),
        "reporter_phone": reporter_phone,
        "reported_phone": reported_phone,
        "reason": reason,
        "status": "pending",
    }).execute()

    if response.data:
        return response.data[0]

    return None


def update_feedback_field(deal_id, role: str, value: str):
    now = datetime.now(timezone.utc).isoformat()

    if role == "buyer":
        payload = {
            "buyer_feedback": value,
            "buyer_feedback_at": now,
        }
    else:
        payload = {
            "seller_feedback": value,
            "seller_feedback_at": now,
        }

    response = (
        supabase.table("deals")
        .update(payload)
        .eq("id", deal_id)
        .execute()
    )

    return response.data


def both_feedback_successful(deal_id):
    deal = get_deal(deal_id)

    if not deal:
        return False

    return (
        deal.get("buyer_feedback") == "successful"
        and deal.get("seller_feedback") == "successful"
    )


def handle_feedback_response(phone: str, message: str):
    session = get_session(phone)

    if not session:
        return None

    if session.get("current_step") != "deal_feedback":
        return None

    temp_data = session.get("temp_data") or {}
    deal_id = temp_data.get("deal_id")
    role = temp_data.get("role")

    if not deal_id or role not in ["buyer", "seller"]:
        clear_session(phone)
        return {
            "handled": True,
            "reply": translate(phone, "feedback_deal_not_found"),
        }

    deal = get_deal(deal_id)

    if not deal:
        clear_session(phone)
        return {
            "handled": True,
            "reply": translate(phone, "feedback_deal_not_found"),
        }

    normalized = str(message).strip().lower()

    if normalized not in ["1", "2", "feedback_success", "feedback_failed"]:
        return {
            "handled": True,
            "reply": translate(phone, "feedback_invalid"),
        }

    if normalized in ["1", "feedback_success"]:
        update_feedback_field(deal_id, role, "successful")
        clear_session(phone)

        refreshed_deal = get_deal(deal_id)

        if (
            refreshed_deal
            and refreshed_deal.get("buyer_feedback") == "successful"
            and refreshed_deal.get("seller_feedback") == "successful"
        ):
            buyer_phone = refreshed_deal.get("buyer_phone")
            seller_phone = refreshed_deal.get("seller_phone")

            if buyer_phone:
                reward_successful_deal(buyer_phone)

            if seller_phone:
                reward_successful_deal(seller_phone)

        return {
            "handled": True,
            "reply": translate(phone, "feedback_success"),
        }

    if normalized in ["2", "feedback_failed"]:
        update_feedback_field(deal_id, role, "problem")
        clear_session(phone)

        if role == "buyer":
            reported_phone = deal.get("seller_phone")
            reason = "Buyer reported a problem after contact sharing."
        else:
            reported_phone = deal.get("buyer_phone")
            reason = "Seller reported a problem after contact sharing."

        create_untrusted_case(
            deal=deal,
            reporter_phone=phone,
            reported_phone=reported_phone,
            reason=reason,
        )

        return {
            "handled": True,
            "reply": translate(phone, "feedback_reported"),
        }

    return {
        "handled": True,
        "reply": translate(phone, "feedback_invalid"),
    }