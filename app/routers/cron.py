from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.config import CRON_SECRET
from app.db.supabase_client import supabase
from app.services.feedback_service import start_feedback_session
from app.services.whatsapp_service import send_whatsapp_buttons
from app.services.language_service import translate

router = APIRouter(prefix="/cron", tags=["Cron"])


def get_listing_for_deal(deal):
    listing_id = deal.get("listing_id")

    if not listing_id:
        return None

    response = (
        supabase.table("listings")
        .select("*")
        .eq("id", listing_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


@router.get("/send-feedback")
def send_feedback(secret: str = Query(None)):
    if secret != CRON_SECRET:
        return {"status": "unauthorized"}

    now = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("deals")
        .select("*")
        .eq("status", "confirmed")
        .eq("feedback_sent", False)
        .lte("feedback_due_at", now)
        .execute()
    )

    deals = response.data or []

    messages_sent = 0

    for deal in deals:
        deal_id = deal.get("id")
        buyer_phone = deal.get("buyer_phone")
        seller_phone = deal.get("seller_phone")

        listing = get_listing_for_deal(deal) or {}
        commodity = listing.get("commodity") or "this item"

        if buyer_phone:
            start_feedback_session(
                phone=buyer_phone,
                deal_id=deal_id,
                role="buyer",
            )

            send_whatsapp_buttons(
                buyer_phone,
                translate(
                    buyer_phone,
                    "feedback_prompt",
                    commodity=commodity,
                ),
                [
                    {"id": "feedback_success", "title": "Successful"},
                    {"id": "feedback_failed", "title": "Problem"},
                ],
            )

            messages_sent += 1

        if seller_phone:
            start_feedback_session(
                phone=seller_phone,
                deal_id=deal_id,
                role="seller",
            )

            send_whatsapp_buttons(
                seller_phone,
                translate(
                    seller_phone,
                    "feedback_prompt",
                    commodity=commodity,
                ),
                [
                    {"id": "feedback_success", "title": "Successful"},
                    {"id": "feedback_failed", "title": "Problem"},
                ],
            )

            messages_sent += 1

        supabase.table("deals").update({
            "feedback_sent": True,
        }).eq("id", deal_id).execute()

    return {
        "status": "done",
        "deals_checked": len(deals),
        "messages_sent": messages_sent,
    }