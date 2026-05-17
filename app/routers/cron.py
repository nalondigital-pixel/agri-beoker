from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.config import CRON_SECRET
from app.db.supabase_client import supabase
from app.services.whatsapp_service import send_whatsapp_message
from app.services.feedback_service import start_feedback_session
from app.services.language_service import translate

router = APIRouter(prefix="/cron", tags=["Cron"])


@router.get("/send-feedback")
def send_feedback_reminders(secret: str = Query(...)):
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
    sent_count = 0

    for deal in deals:
        deal_id = deal.get("id")
        buyer_phone = deal.get("buyer_phone")
        seller_phone = deal.get("seller_phone")
        commodity = "this item"

        listing_id = deal.get("listing_id")

        if listing_id:
            listing_response = (
                supabase.table("listings")
                .select("*")
                .eq("id", listing_id)
                .limit(1)
                .execute()
            )

            if listing_response.data:
                commodity = listing_response.data[0].get("commodity") or "this item"

        if buyer_phone:
            start_feedback_session(buyer_phone, deal_id, "buyer")
            send_whatsapp_message(
                buyer_phone,
                translate(
                    buyer_phone,
                    "feedback_prompt",
                    commodity=commodity,
                ),
            )
            sent_count += 1

        if seller_phone:
            start_feedback_session(seller_phone, deal_id, "seller")
            send_whatsapp_message(
                seller_phone,
                translate(
                    seller_phone,
                    "feedback_prompt",
                    commodity=commodity,
                ),
            )
            sent_count += 1

        supabase.table("deals").update({
            "feedback_sent": True,
        }).eq("id", deal_id).execute()

    return {
        "status": "done",
        "deals_checked": len(deals),
        "messages_sent": sent_count,
    }