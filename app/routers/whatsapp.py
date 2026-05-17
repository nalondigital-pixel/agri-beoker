import os
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import WHATSAPP_VERIFY_TOKEN
from app.services.ai_extractor import extract_market_data
from app.services.db_service import (
    save_listing,
    get_listing_by_id,
    get_active_opposite_listings,
    get_active_listings_by_phone,
    close_listing,
)
from app.services.matching_service import (
    find_matches,
    find_active_listing_matches,
)
from app.services.whatsapp_service import send_whatsapp_message, send_whatsapp_buttons
from app.services.media_service import get_media_url, download_media
from app.services.transcription_service import transcribe_audio
from app.services.session_service import get_session, set_session, clear_session
from app.services.deal_service import (
    create_deal,
    create_deal_between_requests,
    find_pending_deal_by_buyer_phone,
    find_pending_seller_decision,
    get_deals_by_phone,
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
from app.services.registration_service import (
    handle_registration_message,
    get_rules_text,
)
from app.services.language_service import translate
from app.services.feedback_service import (
    handle_feedback_response,
    schedule_deal_feedback,
)
from app.services.message_dedupe_service import (
    has_processed_message,
    mark_message_processed,
)
from app.services.ai_assistant_service import generate_ai_assistant_reply
from app.services.price_intelligence_service import get_price_guidance_for_listing

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])

DAILY_LISTING_LIMIT = 5


def format_trust(phone: str):
    profile = get_profile(phone)

    if not profile:
        return "🛡️ New user"

    trust_score = profile.get("trust_score") or 25
    trust_rank = profile.get("trust_rank") or "New User"
    successful_deals = profile.get("successful_deals") or 0
    total_matches = profile.get("total_matches_allocated") or 0

    return f"🛡️ {trust_score}% {trust_rank} | Deals: {successful_deals}/{total_matches}"


def format_quantity(listing: dict):
    quantity = listing.get("quantity")
    unit = listing.get("unit")

    if quantity is None:
        return "Not specified"

    try:
        quantity_number = float(quantity)

        if quantity_number.is_integer():
            quantity = int(quantity_number)
        else:
            quantity = quantity_number

    except (TypeError, ValueError):
        pass

    if unit:
        return f"{quantity} {unit}"

    return str(quantity)


def format_location(listing: dict):
    location = listing.get("location") or "Unknown location"
    return str(location).title()


def format_price_value(value):
    if value is None:
        return None

    try:
        number = float(value)

        if number.is_integer():
            return int(number)

        return round(number, 2)

    except Exception:
        return value


def format_price_line(listing: dict):
    price = listing.get("price")
    currency = listing.get("currency") or "USD"
    price_per_unit = listing.get("price_per_unit")
    unit = listing.get("unit")

    lines = []

    if price:
        price_value = format_price_value(price)
        lines.append(f"Price: {currency} {price_value}")

    if price_per_unit:
        ppu_value = format_price_value(price_per_unit)

        if unit:
            lines.append(f"Price per {unit}: {currency} {ppu_value}")
        else:
            lines.append(f"Price per unit: {currency} {ppu_value}")

    if not lines:
        return ""

    return "\n".join(lines)


def format_transport_line(listing: dict):
    delivery_option = listing.get("delivery_option")
    transport_needed = listing.get("transport_needed")
    transport_note = listing.get("transport_note")

    label_map = {
        "can_deliver": "Seller can deliver",
        "buyer_collects": "Buyer collects",
        "seller_delivers": "Seller delivers",
        "needs_transport": "Needs transport",
        "will_collect": "Buyer will collect",
        "unknown": "",
        None: "",
    }

    label = label_map.get(delivery_option, "")

    if transport_needed and not label:
        label = "Needs transport"

    if not label and not transport_note:
        return ""

    if transport_note:
        return f"Transport: {label} — {transport_note}" if label else f"Transport: {transport_note}"

    return f"Transport: {label}"


def format_chat_link(phone: str):
    if not phone:
        return "Not available"

    clean_phone = str(phone).replace("+", "").replace(" ", "").strip()
    return f"https://wa.me/{clean_phone}"


def format_deal_status(status: str):
    status_map = {
        "buyer_alerted": "Waiting for buyer response",
        "buyer_interested": "Waiting for seller approval",
        "confirmed": "Confirmed — contact shared",
        "seller_waiting": "Seller waiting for better offer",
        "buyer_declined": "Buyer declined",
        "cancelled": "Cancelled",
        "fulfilled": "Fulfilled",
        "closed": "Closed",
        "expired": "Expired",
    }

    return status_map.get(status, status or "Unknown")


def show_main_menu(phone: str):
    send_whatsapp_buttons(
        phone,
        translate(phone, "main_menu"),
        [
            {"id": "menu_buy", "title": "Buy"},
            {"id": "menu_sell", "title": "Sell"},
            {"id": "menu_deals", "title": "My Deals"},
        ],
    )


def show_ai_assistant_menu(phone: str, incoming_message: str):
    profile = get_profile(phone) or {}

    user_name = profile.get("name")
    user_language = profile.get("language") or "english"

    ai_reply = generate_ai_assistant_reply(
        user_message=incoming_message,
        user_name=user_name,
        user_language=user_language,
    )

    send_whatsapp_buttons(
        phone,
        ai_reply,
        [
            {"id": "menu_buy", "title": "Buy"},
            {"id": "menu_sell", "title": "Sell"},
            {"id": "menu_deals", "title": "My Deals"},
        ],
    )


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

    if message.startswith("cancel_request_"):
        return message

    if message.startswith("fulfill_request_"):
        return message

    command_map = {
        "buyer_interested": "1",
        "buyer_not_interested": "2",

        "seller_share_contacts": "1",
        "seller_wait_better": "2",
        "seller_cancel": "3",

        "feedback_success": "1",
        "feedback_failed": "2",

        "registration_agree_terms": "registration_agree_terms",

        "menu_buy": "menu_buy",
        "menu_sell": "menu_sell",
        "menu_deals": "menu_deals",

        "confirm_listing": "confirm_listing",
        "edit_listing": "edit_listing",

        "transport_can_deliver": "transport_can_deliver",
        "transport_buyer_collects": "transport_buyer_collects",
        "transport_need": "transport_need",
        "transport_will_collect": "transport_will_collect",
        "transport_skip": "transport_skip",
    }

    return command_map.get(message, message)


def get_missing_listing_fields(listing: dict):
    missing = []

    commodity = listing.get("commodity")
    quantity = listing.get("quantity")
    location = listing.get("location")

    if not commodity or str(commodity).strip() in ["", "unknown", "none"]:
        missing.append("commodity")

    try:
        quantity_number = float(quantity or 0)
    except Exception:
        quantity_number = 0

    if quantity_number <= 0:
        missing.append("quantity")

    if not location or str(location).strip() in ["", "unknown", "none"]:
        missing.append("location")

    return missing


def get_missing_field_question(field: str, listing: dict):
    intent = listing.get("intent") or "sell"

    if field == "commodity":
        if intent == "buy":
            return "What product do you want to buy? Example: beef, maize, goats, potatoes."
        return "What product are you selling? Example: beef, maize, goats, potatoes."

    if field == "quantity":
        return "What quantity? Please include unit if possible. Example: 20 kg, 10 bags, 4 goats."

    if field == "location":
        return "Where is it located? Example: Rimuka Kadoma, Chegutu, Harare."

    return "Please send the missing detail."


def update_listing_with_missing_answer(pending_listing: dict, field: str, answer: str, phone: str):
    extracted = extract_market_data(answer, reporter_phone=phone)

    if field == "commodity":
        commodity = extracted.get("commodity") or answer.strip().lower()
        pending_listing["commodity"] = commodity

    elif field == "quantity":
        quantity = extracted.get("quantity")
        unit = extracted.get("unit")

        if quantity:
            pending_listing["quantity"] = quantity

        if unit:
            pending_listing["unit"] = unit
            pending_listing["raw_quantity_text"] = f"{quantity} {unit}".strip()

        if not quantity:
            try:
                pending_listing["quantity"] = float(answer.strip())
            except Exception:
                pass

    elif field == "location":
        location = extracted.get("location") or answer.strip()
        pending_listing["location"] = location

    price = extracted.get("price")
    price_per_unit = extracted.get("price_per_unit")
    currency = extracted.get("currency")

    if price and not pending_listing.get("price"):
        pending_listing["price"] = price

    if price_per_unit and not pending_listing.get("price_per_unit"):
        pending_listing["price_per_unit"] = price_per_unit

    if currency and not pending_listing.get("currency"):
        pending_listing["currency"] = currency

    delivery_option = extracted.get("delivery_option")
    transport_note = extracted.get("transport_note")

    if delivery_option and delivery_option != "unknown":
        pending_listing["delivery_option"] = delivery_option

    if transport_note:
        pending_listing["transport_note"] = transport_note

    if extracted.get("transport_needed"):
        pending_listing["transport_needed"] = True

    return pending_listing


def should_ask_transport(listing: dict):
    delivery_option = listing.get("delivery_option")

    return not delivery_option or delivery_option == "unknown"


def send_transport_question(phone: str, listing: dict):
    intent = listing.get("intent")

    if intent == "buy":
        send_whatsapp_buttons(
            phone,
            "Transport/delivery question:\n\nHow will you handle collection or delivery?",
            [
                {"id": "transport_need", "title": "Need Transport"},
                {"id": "transport_will_collect", "title": "Will Collect"},
                {"id": "transport_skip", "title": "Skip"},
            ],
        )
        return

    send_whatsapp_buttons(
        phone,
        "Transport/delivery question:\n\nCan you deliver, or should the buyer collect?",
        [
            {"id": "transport_can_deliver", "title": "Can Deliver"},
            {"id": "transport_buyer_collects", "title": "Buyer Collects"},
            {"id": "transport_skip", "title": "Skip"},
        ],
    )


def apply_transport_answer(listing: dict, incoming_message: str):
    if incoming_message == "transport_can_deliver":
        listing["delivery_option"] = "can_deliver"
        listing["transport_needed"] = False
        listing["transport_note"] = "Seller can deliver"

    elif incoming_message == "transport_buyer_collects":
        listing["delivery_option"] = "buyer_collects"
        listing["transport_needed"] = False
        listing["transport_note"] = "Buyer collects"

    elif incoming_message == "transport_need":
        listing["delivery_option"] = "needs_transport"
        listing["transport_needed"] = True
        listing["transport_note"] = "Buyer needs transport"

    elif incoming_message == "transport_will_collect":
        listing["delivery_option"] = "will_collect"
        listing["transport_needed"] = False
        listing["transport_note"] = "Buyer will collect"

    elif incoming_message == "transport_skip":
        listing["delivery_option"] = "unknown"
        listing["transport_needed"] = False
        listing["transport_note"] = ""

    return listing


def build_listing_confirmation_message(extracted: dict):
    intent = (extracted.get("intent") or "unknown").upper()
    commodity = extracted.get("commodity") or "Unknown commodity"
    quantity = format_quantity(extracted)
    location = format_location(extracted)
    confidence = extracted.get("confidence", 0)

    try:
        confidence_percent = int(float(confidence) * 100)
    except Exception:
        confidence_percent = 0

    price_text = format_price_line(extracted)
    transport_text = format_transport_line(extracted)
    price_guidance = get_price_guidance_for_listing(extracted)

    optional_blocks = ""

    if price_text:
        optional_blocks += f"{price_text}\n"

    if transport_text:
        optional_blocks += f"{transport_text}\n"

    if price_guidance:
        optional_blocks += f"\n{price_guidance}\n"

    return (
        "Please confirm what I understood:\n\n"
        f"Type: {intent}\n"
        f"Commodity: {commodity}\n"
        f"Quantity: {quantity}\n"
        f"Location: {location}\n"
        f"{optional_blocks}"
        f"AI Confidence: {confidence_percent}%\n\n"
        "Is this correct?"
    )


def send_listing_confirmation(phone: str, extracted: dict):
    send_whatsapp_buttons(
        phone,
        build_listing_confirmation_message(extracted),
        [
            {"id": "confirm_listing", "title": "Confirm"},
            {"id": "edit_listing", "title": "Edit"},
        ],
    )


def send_match_alert_to_buyer(buyer_phone, seller_phone, listing, match_data):
    match_reasons = ", ".join(match_data.get("_match_reasons", []))

    price_text = format_price_line(listing)
    transport_text = format_transport_line(listing)

    extra = ""

    if price_text:
        extra += f"\n\n{price_text}"

    if transport_text:
        extra += f"\n{transport_text}"

    buyer_message = translate(
        buyer_phone,
        "buyer_match_alert",
        commodity=listing.get("commodity"),
        quantity=format_quantity(listing),
        location=format_location(listing),
        distance_match=match_data.get("_geo_message", "Location match"),
        seller_trust=format_trust(seller_phone),
        match_score=match_data.get("_match_score", 0),
        match_reasons=match_reasons,
    )

    buyer_message = buyer_message + extra

    send_whatsapp_buttons(
        buyer_phone,
        buyer_message,
        [
            {"id": "buyer_interested", "title": "Interested"},
            {"id": "buyer_not_interested", "title": "Not Interested"},
        ],
    )


def notify_active_request_matches(new_listing):
    active_opposites = get_active_opposite_listings(
        new_listing.get("intent"),
        exclude_phone=new_listing.get("seller_phone"),
    )

    active_matches = find_active_listing_matches(new_listing, active_opposites)

    sent_count = 0

    for matched_request in active_matches:
        deal = create_deal_between_requests(new_listing, matched_request)

        if not deal:
            continue

        buyer_phone = deal.get("buyer_phone")
        seller_phone = deal.get("seller_phone")

        if not buyer_phone or not seller_phone:
            continue

        if new_listing.get("intent") == "sell":
            seller_listing = new_listing
            match_data = matched_request
        else:
            seller_listing = matched_request
            match_data = matched_request

        send_match_alert_to_buyer(
            buyer_phone=buyer_phone,
            seller_phone=seller_phone,
            listing=seller_listing,
            match_data=match_data,
        )

        send_whatsapp_message(
            seller_phone,
            translate(seller_phone, "listing_saved_with_matches", match_count=1),
        )

        sent_count += 1

    return sent_count


def build_my_deals_message(phone: str):
    deals = get_deals_by_phone(phone)

    if not deals:
        return (
            "📋 My Deals\n\n"
            "You do not have any deals yet.\n\n"
            "Use Buy or Sell from the menu to create a request."
        )

    message_parts = ["📋 My Deals\n"]

    for index, deal in enumerate(deals, start=1):
        listing = deal.get("listing") or {}

        role = "Buyer" if deal.get("buyer_phone") == phone else "Seller"
        status = format_deal_status(deal.get("status"))

        commodity = listing.get("commodity") or "Unknown commodity"
        quantity = format_quantity(listing)
        location = format_location(listing)
        price_text = format_price_line(listing)
        transport_text = format_transport_line(listing)

        deal_text = (
            f"{index}. {commodity}\n"
            f"Role: {role}\n"
            f"Quantity: {quantity}\n"
            f"Location: {location}\n"
        )

        if price_text:
            deal_text += f"{price_text}\n"

        if transport_text:
            deal_text += f"{transport_text}\n"

        deal_text += f"Status: {status}"

        if deal.get("status") == "confirmed":
            if role == "Buyer":
                seller_phone = deal.get("seller_phone")
                deal_text += f"\nChat with seller: {format_chat_link(seller_phone)}"
            else:
                buyer_phone = deal.get("buyer_phone")
                deal_text += f"\nChat with buyer: {format_chat_link(buyer_phone)}"

        message_parts.append(deal_text)

    return "\n\n".join(message_parts)


def build_request_card(listing: dict):
    intent = (listing.get("intent") or "request").upper()
    commodity = listing.get("commodity") or "Unknown commodity"
    quantity = format_quantity(listing)
    location = format_location(listing)
    price_text = format_price_line(listing)
    transport_text = format_transport_line(listing)

    optional_block = ""

    if price_text:
        optional_block += f"{price_text}\n"

    if transport_text:
        optional_block += f"{transport_text}\n"

    return (
        f"📌 Active Request\n\n"
        f"Type: {intent}\n"
        f"Commodity: {commodity}\n"
        f"Quantity: {quantity}\n"
        f"Location: {location}\n"
        f"{optional_block}\n"
        f"What do you want to do with this request?"
    )


def send_active_request_buttons(phone: str):
    active_requests = get_active_listings_by_phone(phone)

    if not active_requests:
        send_whatsapp_message(
            phone,
            "You have no active requests right now.",
        )
        return 0

    send_whatsapp_message(
        phone,
        f"You have {len(active_requests)} active request(s).",
    )

    sent_count = 0

    for request_item in active_requests:
        listing_id = request_item.get("id")

        if not listing_id:
            continue

        send_whatsapp_buttons(
            phone,
            build_request_card(request_item),
            [
                {
                    "id": f"cancel_request_{listing_id}",
                    "title": "Cancel",
                },
                {
                    "id": f"fulfill_request_{listing_id}",
                    "title": "Done",
                },
            ],
        )

        sent_count += 1

    return sent_count


def handle_request_action(phone: str, incoming_message: str):
    if incoming_message.startswith("cancel_request_"):
        listing_id = incoming_message.replace("cancel_request_", "").strip()

        updated = close_listing(
            listing_id=listing_id,
            phone=phone,
            status="cancelled",
        )

        if updated:
            send_whatsapp_message(
                phone,
                "✅ Request cancelled. It will no longer be matched.",
            )
            return True

        send_whatsapp_message(
            phone,
            "Could not cancel this request. It may already be closed.",
        )
        return True

    if incoming_message.startswith("fulfill_request_"):
        listing_id = incoming_message.replace("fulfill_request_", "").strip()

        updated = close_listing(
            listing_id=listing_id,
            phone=phone,
            status="fulfilled",
        )

        if updated:
            send_whatsapp_message(
                phone,
                "✅ Request marked as done. It will no longer be matched.",
            )
            return True

        send_whatsapp_message(
            phone,
            "Could not update this request. It may already be closed.",
        )
        return True

    return False


def prepare_listing_for_confirmation(sender_phone: str, listing: dict, original_step: str):
    missing_fields = get_missing_listing_fields(listing)

    if missing_fields:
        set_session(
            sender_phone,
            "collect_missing_listing_field",
            {
                "pending_listing": listing,
                "missing_fields": missing_fields,
                "original_step": original_step,
            },
        )

        send_whatsapp_message(
            sender_phone,
            get_missing_field_question(missing_fields[0], listing),
        )

        return {
            "status": "missing_info_requested",
            "missing_field": missing_fields[0],
        }

    if should_ask_transport(listing):
        set_session(
            sender_phone,
            "transport_question",
            {
                "pending_listing": listing,
                "original_step": original_step,
            },
        )

        send_transport_question(sender_phone, listing)

        return {
            "status": "transport_question_sent",
        }

    set_session(
        sender_phone,
        "confirm_listing",
        {
            "pending_listing": listing,
            "original_step": original_step,
        },
    )

    send_listing_confirmation(sender_phone, listing)

    return {
        "status": "listing_confirmation_sent",
        "extracted": listing,
    }


def save_confirmed_listing_and_match(sender_phone: str, extracted: dict):
    listing = save_listing(extracted)

    if not listing:
        send_whatsapp_message(
            sender_phone,
            "Sorry, your request could not be saved. Please try again.",
        )
        return {
            "status": "error",
            "message": "Listing could not be saved",
        }

    print("\n========== SAVED LISTING ==========")
    print(listing)

    active_match_count = notify_active_request_matches(listing)

    matches = []

    if listing.get("intent") == "sell":
        matches = find_matches(listing)

    if not matches and active_match_count == 0:
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

        send_match_alert_to_buyer(
            buyer_phone=buyer_phone,
            seller_phone=sender_phone,
            listing=listing,
            match_data=buyer,
        )

        sent_alerts.append({
            "buyer": buyer,
            "deal": deal,
        })

    total_sent = len(sent_alerts) + active_match_count

    send_whatsapp_message(
        sender_phone,
        translate(
            sender_phone,
            "listing_saved_with_matches",
            match_count=total_sent,
        ),
    )

    return {
        "status": "saved",
        "listing": listing,
        "matches": matches,
        "active_request_matches": active_match_count,
        "alerts_sent": sent_alerts,
    }


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
        whatsapp_message_id = message_data.get("id")

        if whatsapp_message_id and has_processed_message(whatsapp_message_id):
            print("Duplicate WhatsApp message ignored:", whatsapp_message_id)
            return {"status": "duplicate_message_ignored"}

        if whatsapp_message_id:
            mark_message_processed(whatsapp_message_id, sender_phone)

        incoming_message = extract_incoming_message(message_data)

        if not incoming_message:
            return {"status": "ignored_unsupported_message"}

        if incoming_message == "VOICE_TRANSCRIPTION_NOT_READY":
            send_whatsapp_message(
                sender_phone,
                translate(sender_phone, "voice_not_ready"),
            )
            return {"status": "voice_received_not_transcribed"}

        incoming_message = normalize_command(incoming_message)

        print("\n========== INCOMING MESSAGE ==========")
        print("FROM:", sender_phone)
        print("MESSAGE ID:", whatsapp_message_id)
        print("MESSAGE:", incoming_message)

        if is_blocked_user(sender_phone):
            return {"status": "blocked_user_ignored"}

        if handle_request_action(sender_phone, incoming_message):
            return {"status": "request_action_handled"}

        feedback_result = handle_feedback_response(sender_phone, incoming_message)

        if feedback_result and feedback_result.get("handled"):
            send_whatsapp_message(sender_phone, feedback_result.get("reply"))
            return {"status": "feedback_handled"}

        if not has_completed_registration(sender_phone):
            reply = handle_registration_message(sender_phone, incoming_message)

            if reply == "__SHOW_RULES_AGREE_BUTTON__":
                profile = get_profile(sender_phone) or {}
                language = profile.get("language") or "english"

                session = get_session(sender_phone)
                temp_data = session.get("temp_data") if session else {}
                language = temp_data.get("language") or language

                send_whatsapp_buttons(
                    sender_phone,
                    get_rules_text(language),
                    [
                        {"id": "registration_agree_terms", "title": "Agree"},
                    ],
                )

                return {"status": "registration_rules_button_sent"}

            send_whatsapp_message(sender_phone, reply)

            if (
                "Registration complete" in reply
                or "Wapedza kunyoresa" in reply
                or "Usuqedile ukubhalisa" in reply
            ):
                show_main_menu(sender_phone)

            return {"status": "registration_flow"}

        session = get_session(sender_phone)

        if session and session.get("current_step") == "collect_missing_listing_field":
            temp_data = session.get("temp_data") or {}
            pending_listing = temp_data.get("pending_listing") or {}
            missing_fields = temp_data.get("missing_fields") or []
            original_step = temp_data.get("original_step")

            if not missing_fields:
                return prepare_listing_for_confirmation(
                    sender_phone,
                    pending_listing,
                    original_step,
                )

            current_field = missing_fields[0]

            pending_listing = update_listing_with_missing_answer(
                pending_listing=pending_listing,
                field=current_field,
                answer=incoming_message,
                phone=sender_phone,
            )

            missing_fields = get_missing_listing_fields(pending_listing)

            if missing_fields:
                set_session(
                    sender_phone,
                    "collect_missing_listing_field",
                    {
                        "pending_listing": pending_listing,
                        "missing_fields": missing_fields,
                        "original_step": original_step,
                    },
                )

                send_whatsapp_message(
                    sender_phone,
                    get_missing_field_question(missing_fields[0], pending_listing),
                )

                return {
                    "status": "missing_info_requested",
                    "missing_field": missing_fields[0],
                }

            return prepare_listing_for_confirmation(
                sender_phone,
                pending_listing,
                original_step,
            )

        if session and session.get("current_step") == "transport_question":
            temp_data = session.get("temp_data") or {}
            pending_listing = temp_data.get("pending_listing") or {}
            original_step = temp_data.get("original_step")

            pending_listing = apply_transport_answer(
                pending_listing,
                incoming_message,
            )

            set_session(
                sender_phone,
                "confirm_listing",
                {
                    "pending_listing": pending_listing,
                    "original_step": original_step,
                },
            )

            send_listing_confirmation(sender_phone, pending_listing)

            return {"status": "listing_confirmation_sent_after_transport"}

        if session and session.get("current_step") == "confirm_listing":
            temp_data = session.get("temp_data") or {}
            pending_listing = temp_data.get("pending_listing") or {}
            original_step = temp_data.get("original_step")

            if incoming_message == "confirm_listing":
                clear_session(sender_phone)
                return save_confirmed_listing_and_match(sender_phone, pending_listing)

            if incoming_message == "edit_listing":
                if original_step == "create_buy_request":
                    set_session(sender_phone, "create_buy_request", {})
                    send_whatsapp_message(
                        sender_phone,
                        "Okay, please send the buy request again.\n\nExample: 15 kg beef in Rimuka, Kadoma budget $60",
                    )
                    return {"status": "edit_buy_listing"}

                set_session(sender_phone, "create_sell_listing", {})
                send_whatsapp_message(
                    sender_phone,
                    "Okay, please send the sell request again.\n\nExample: 20 kg beef in Rimuka, Kadoma for $80",
                )
                return {"status": "edit_sell_listing"}

            send_listing_confirmation(sender_phone, pending_listing)
            return {"status": "waiting_for_listing_confirmation"}

        if incoming_message.lower() in ["hi", "hello", "menu", "start", "help"]:
            show_main_menu(sender_phone)
            return {"status": "main_menu"}

        if incoming_message == "menu_buy":
            set_session(sender_phone, "create_buy_request", {})

            send_whatsapp_message(
                sender_phone,
                translate(sender_phone, "buy_prompt"),
            )

            return {"status": "buy_flow_started"}

        if incoming_message == "menu_sell":
            set_session(sender_phone, "create_sell_listing", {})

            send_whatsapp_message(
                sender_phone,
                translate(sender_phone, "sell_prompt"),
            )

            return {"status": "sell_flow_started"}

        if incoming_message == "menu_deals":
            send_whatsapp_message(
                sender_phone,
                build_my_deals_message(sender_phone),
            )

            active_count = send_active_request_buttons(sender_phone)

            return {
                "status": "my_deals_and_requests_shown",
                "active_requests": active_count,
            }

        forced_intent = None
        original_step = None

        if session and session.get("current_step") == "create_buy_request":
            forced_intent = "buy"
            original_step = "create_buy_request"

        elif session and session.get("current_step") == "create_sell_listing":
            forced_intent = "sell"
            original_step = "create_sell_listing"

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

                buyer_chat_link = format_chat_link(seller_phone)
                seller_chat_link = format_chat_link(buyer_phone)

                send_whatsapp_message(
                    buyer_phone,
                    translate(
                        buyer_phone,
                        "deal_approved_buyer",
                        seller_name=seller_name,
                        seller_phone=seller_phone,
                        commodity=listing.get("commodity"),
                        quantity=format_quantity(listing),
                        location=format_location(listing),
                    )
                    + f"\n\nChat with seller:\n{buyer_chat_link}",
                )

                send_whatsapp_message(
                    seller_phone,
                    translate(
                        seller_phone,
                        "contact_shared_seller",
                        buyer_name=buyer_name,
                        buyer_phone=buyer_phone,
                        commodity=listing.get("commodity"),
                        quantity=format_quantity(listing),
                        location=format_location(listing),
                    )
                    + f"\n\nChat with buyer:\n{seller_chat_link}",
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
                show_main_menu(sender_phone)
                return {"status": "no_pending_deal_show_menu"}

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
                quantity=format_quantity(listing),
                location=format_location(listing),
            )

            price_text = format_price_line(listing)
            transport_text = format_transport_line(listing)

            if price_text:
                seller_prompt += f"\n\n{price_text}"

            if transport_text:
                seller_prompt += f"\n{transport_text}"

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
                    translate(sender_phone, "buyer_declined"),
                )

                return {"status": "buyer_declined"}

            show_main_menu(sender_phone)
            return {"status": "no_pending_deal_show_menu"}

        if not forced_intent:
            show_ai_assistant_menu(sender_phone, incoming_message)

            return {
                "status": "ai_assistant_reply_sent",
                "message": incoming_message,
            }

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

        extracted["intent"] = forced_intent
        extracted["raw"] = incoming_message
        extracted["seller_phone"] = sender_phone

        print("\n========== EXTRACTED MARKET DATA ==========")
        print(extracted)

        return prepare_listing_for_confirmation(
            sender_phone,
            extracted,
            original_step,
        )

    except Exception as e:
        print("Webhook error:", e)
        return {"status": "error", "message": str(e)}