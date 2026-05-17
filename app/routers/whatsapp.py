import os
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import WHATSAPP_VERIFY_TOKEN
from app.services.ai_extractor import extract_market_data
from app.services.db_service import save_listing, get_listing_by_id
from app.services.matching_service import find_matches
from app.services.whatsapp_service import send_whatsapp_message, send_whatsapp_buttons
from app.services.media_service import get_media_url, download_media
from app.services.transcription_service import transcribe_audio
from app.services.deal_service import (
    create_deal,
    find_pending_deal_by_buyer_phone,
    find_pending_seller_decision,
    update_deal_status,
    update_buyer_decision,
    update_seller_decision,
)
from app.services.trust_service import (
    is_blocked_user,
    count_today_listings_by_seller,
    create_fraud_report,
)
from app.services.profile_service import (
    has_completed_registration,
    get_display_name,
    get_profile,
)
from app.services.registration_service import handle_registration_message
from app.services.language_service import translate
from app.services.feedback_service import (
    handle_feedback_response,
    schedule_deal_feedback,
)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])

DAILY_LISTING_LIMIT = 5


def format_trust(phone: str):
    profile = get_profile(phone)

    if not profile:
        return "🛡️ New user"

    trust_score = profile.get("trust_score") or 25
    trust_rank = profile.get("trust_rank") or "New Seller"
    successful_deals = profile.get("successful_deals") or 0
    total_matches = profile.get("total_matches_allocated") or 0

    return f"🛡️ {trust_score}% {trust_rank} | Deals: {successful_deals}/{total_matches}"


def extract_incoming_message(message_data: dict):
    if "text" in message_data:
        return message_data["text"]["body"].strip()

    if "interactive" in message_data:
        interactive = message_data["interactive"]

        if interactive.get("type") == "button_reply":
            return interactive["button_reply"]["id"]

    if "audio" in message_data:
        media_id = message_data["audio"]["id"]
        media_url = get_media_url(media_id)

        if not media_url:
            return None

        os.makedirs("tmp", exist_ok=True)
        audio_path = f"tmp/{uuid4()}.ogg"

        download_media(media_url, audio_path)

        transcript = transcribe_audio(audio_path)

        if transcript:
            return transcript.strip()

        return "VOICE_TRANSCRIPTION_NOT_READY"

    return None


def normalize_command(message: str):
    message = message.strip().lower()

    command_map = {
        "buyer_interested": "1",
        "buyer_not_interested": "2",
        "seller_share_contacts": "1",
        "seller_wait_better": "2",
        "seller_cancel": "3",
        "feedback_success": "1",
        "feedback_failed": "2",
    }

    return command_map.get(message, message)


@router.get("/")
def verify_webhook(request: Request):
    params = request.query_params

    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge"))

    return {"status": "failed"}


@router.post("/")
async def receive_message(request: Request):
    data = await request.json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return {"status": "ignored_non_message_event"}

        message_data = value["messages"][0]
        sender_phone = message_data["from"]

        incoming_message = extract_incoming_message(message_data)

        if not incoming_message:
            return {"status": "ignored_unsupported_message"}

        if incoming_message == "VOICE_TRANSCRIPTION_NOT_READY":
            send_whatsapp_message(
                sender_phone,
                "🎤 Voice note received, but voice transcription is not connected yet. Please type your listing for now.",
            )
            return {"status": "voice_received_not_transcribed"}

        incoming_message = normalize_command(incoming_message)

        print("\n========== INCOMING MESSAGE ==========")
        print("FROM:", sender_phone)
        print("MESSAGE:", incoming_message)

        if is_blocked_user(sender_phone):
            return {"status": "blocked_user_ignored"}

        feedback_result = handle_feedback_response(sender_phone, incoming_message)

        if feedback_result and feedback_result.get("handled"):
            send_whatsapp_message(sender_phone, feedback_result.get("reply"))
            return {"status": "feedback_handled"}

        if not has_completed_registration(sender_phone):
            reply = handle_registration_message(sender_phone, incoming_message)
            send_whatsapp_message(sender_phone, reply)
            return {"status": "registration_flow"}

        if incoming_message.lower().startswith("report "):
            parts = incoming_message.split(" ", 2)

            if len(parts) < 3:
                send_whatsapp_message(
                    sender_phone,
                    translate(sender_phone, "invalid_report_format"),
                )
                return {"status": "invalid_report_format"}

            reported_phone = parts[1].strip()
            reason = parts[2].strip()

            report = create_fraud_report(
                reporter_phone=sender_phone,
                reported_phone=reported_phone,
                reason=reason,
            )

            send_whatsapp_message(
                sender_phone,
                translate(sender_phone, "report_received"),
            )

            return {"status": "fraud_report_created", "report": report}

        seller_deal = find_pending_seller_decision(sender_phone)

        if seller_deal and incoming_message in ["1", "2", "3"]:
            listing = get_listing_by_id(seller_deal.get("listing_id"))

            if not listing:
                send_whatsapp_message(
                    sender_phone,
                    "Deal found, but listing details are missing.",
                )
                return {"status": "listing_missing"}

            if incoming_message == "1":
                update_seller_decision(seller_deal.get("id"), "share_contacts")
                update_deal_status(seller_deal.get("id"), "confirmed")
                schedule_deal_feedback(seller_deal.get("id"))

                buyer_phone = seller_deal.get("buyer_phone")
                seller_phone = seller_deal.get("seller_phone")

                seller_name = get_display_name(seller_phone)
                buyer_name = get_display_name(buyer_phone)

                send_whatsapp_message(
                    buyer_phone,
                    translate(
                        buyer_phone,
                        "deal_approved_buyer",
                        seller_name=seller_name,
                        seller_phone=seller_phone,
                        commodity=listing.get("commodity"),
                        quantity=listing.get("quantity"),
                        location=listing.get("location"),
                    ),
                )

                send_whatsapp_message(
                    seller_phone,
                    translate(
                        seller_phone,
                        "contact_shared_seller",
                        buyer_name=buyer_name,
                        buyer_phone=buyer_phone,
                        commodity=listing.get("commodity"),
                        quantity=listing.get("quantity"),
                        location=listing.get("location"),
                    ),
                )

                return {"status": "deal_confirmed_by_seller"}

            if incoming_message == "2":
                update_seller_decision(seller_deal.get("id"), "wait_better_offer")
                update_deal_status(seller_deal.get("id"), "seller_waiting")

                send_whatsapp_message(
                    sender_phone,
                    translate(sender_phone, "seller_waiting_better_offer"),
                )

                return {"status": "seller_waiting_for_better_offer"}

            if incoming_message == "3":
                update_seller_decision(seller_deal.get("id"), "cancel")
                update_deal_status(seller_deal.get("id"), "cancelled")

                send_whatsapp_message(
                    sender_phone,
                    translate(sender_phone, "seller_cancelled_deal"),
                )

                return {"status": "seller_cancelled_deal"}

        if incoming_message.lower() in ["yes", "1"]:
            deal = find_pending_deal_by_buyer_phone(sender_phone)

            if not deal:
                send_whatsapp_message(
                    sender_phone,
                    "No pending deal found for your number.",
                )
                return {"status": "no_pending_deal"}

            listing = get_listing_by_id(deal.get("listing_id"))

            if not listing:
                send_whatsapp_message(
                    sender_phone,
                    "Deal found, but listing details are missing.",
                )
                return {"status": "listing_missing"}

            seller_phone = deal.get("seller_phone") or listing.get("seller_phone")
            buyer_phone = deal.get("buyer_phone")

            update_buyer_decision(deal.get("id"), "interested")
            update_deal_status(deal.get("id"), "buyer_interested")

            buyer_name = get_display_name(buyer_phone)

            send_whatsapp_message(
                buyer_phone,
                translate(buyer_phone, "buyer_interest_received"),
            )

            seller_prompt = translate(
                seller_phone,
                "seller_approval_prompt",
                buyer_name=buyer_name,
                commodity=listing.get("commodity"),
                quantity=listing.get("quantity"),
                location=listing.get("location"),
            )

            send_whatsapp_buttons(
                seller_phone,
                seller_prompt,
                [
                    {"id": "seller_share_contacts", "title": "Share"},
                    {"id": "seller_wait_better", "title": "Wait"},
                    {"id": "seller_cancel", "title": "Cancel"},
                ],
            )

            return {"status": "seller_approval_requested"}

        if incoming_message == "2":
            deal = find_pending_deal_by_buyer_phone(sender_phone)

            if deal:
                update_buyer_decision(deal.get("id"), "not_interested")
                update_deal_status(deal.get("id"), "buyer_declined")

                send_whatsapp_message(
                    sender_phone,
                    "✅ Noted. We will not continue with this match.",
                )

                return {"status": "buyer_declined"}

        today_count = count_today_listings_by_seller(sender_phone)

        if today_count >= DAILY_LISTING_LIMIT:
            send_whatsapp_message(
                sender_phone,
                translate(sender_phone, "daily_limit_reached"),
            )
            return {"status": "daily_limit_reached", "limit": DAILY_LISTING_LIMIT}

        extracted = extract_market_data(
            incoming_message,
            reporter_phone=sender_phone,
        )
        extracted["raw"] = incoming_message
        extracted["seller_phone"] = sender_phone

        listing = save_listing(extracted)

        if not listing:
            return {"status": "error", "message": "Listing could not be saved"}

        matches = find_matches(extracted)

        if not matches:
            send_whatsapp_message(
                sender_phone,
                translate(sender_phone, "listing_saved_no_matches"),
            )

            return {
                "status": "listing_saved_no_matches",
                "listing": listing,
                "matches": [],
            }

        sent_alerts = []

        for buyer in matches:
            buyer_phone = buyer.get("phone")

            if not buyer_phone:
                continue

            deal = create_deal(
                listing_id=listing.get("id"),
                buyer=buyer,
                seller_phone=sender_phone,
            )

            if not deal:
                continue

            match_reasons = ", ".join(buyer.get("_match_reasons", []))

            buyer_message = translate(
                buyer_phone,
                "buyer_match_alert",
                commodity=extracted.get("commodity"),
                quantity=extracted.get("quantity"),
                location=extracted.get("location"),
                distance_match=buyer.get("_geo_message", "Location match"),
                seller_trust=format_trust(sender_phone),
                match_score=buyer.get("_match_score", 0),
                match_reasons=match_reasons,
            )

            send_whatsapp_buttons(
                buyer_phone,
                buyer_message,
                [
                    {"id": "buyer_interested", "title": "Interested"},
                    {"id": "buyer_not_interested", "title": "Not Interested"},
                ],
            )

            sent_alerts.append({
                "buyer": buyer,
                "deal": deal,
            })

        send_whatsapp_message(
            sender_phone,
            translate(
                sender_phone,
                "listing_saved_with_matches",
                match_count=len(sent_alerts),
            ),
        )

        return {
            "status": "saved",
            "listing": listing,
            "matches": matches,
            "alerts_sent": sent_alerts,
        }

    except Exception as e:
        print("Webhook error:", e)
        return {"status": "error", "message": str(e)}