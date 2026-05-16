from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import WHATSAPP_VERIFY_TOKEN
from app.services.ai_extractor import extract_market_data
from app.services.db_service import save_listing, get_listing_by_id
from app.services.matching_service import find_matches
from app.services.whatsapp_service import send_whatsapp_message
from app.services.deal_service import (
    create_deal,
    find_pending_deal_by_buyer_phone,
    update_deal_status,
)
from app.services.trust_service import is_blocked_user

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])


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

        if "text" not in message_data:
            return {"status": "ignored_non_text_message"}

        incoming_message = message_data["text"]["body"].strip()
        sender_phone = message_data["from"]

        print("\n========== INCOMING MESSAGE ==========")
        print("FROM:", sender_phone)
        print("MESSAGE:", incoming_message)

        if is_blocked_user(sender_phone):
            print("Blocked user ignored:", sender_phone)
            return {"status": "blocked_user_ignored"}

        if incoming_message.lower() == "yes":
            deal = find_pending_deal_by_buyer_phone(sender_phone)

            if not deal:
                send_whatsapp_message(
                    sender_phone,
                    "No pending deal found for your number."
                )
                return {"status": "no_pending_deal"}

            listing = get_listing_by_id(deal.get("listing_id"))

            if not listing:
                send_whatsapp_message(
                    sender_phone,
                    "Deal found, but listing details are missing."
                )
                return {"status": "listing_missing"}

            seller_phone = listing.get("seller_phone")
            buyer_phone = deal.get("buyer_phone")

            buyer_message = f"""
✅ DEAL CONFIRMED

Seller contact: {seller_phone}

Commodity: {listing.get('commodity')}
Quantity: {listing.get('quantity')}
Location: {listing.get('location')}

Please contact the seller to arrange payment/collection.
"""

            seller_message = f"""
✅ BUYER INTEREST CONFIRMED

Buyer contact: {buyer_phone}

Commodity: {listing.get('commodity')}
Quantity: {listing.get('quantity')}
Location: {listing.get('location')}

Please contact the buyer to complete the deal.
"""

            send_whatsapp_message(buyer_phone, buyer_message)

            if seller_phone:
                send_whatsapp_message(seller_phone, seller_message)

            update_deal_status(deal.get("id"), "confirmed")

            return {
                "status": "deal_confirmed",
                "deal": deal,
                "listing": listing,
            }

        extracted = extract_market_data(incoming_message)
        extracted["raw"] = incoming_message
        extracted["seller_phone"] = sender_phone

        listing = save_listing(extracted)

        if not listing:
            return {
                "status": "error",
                "message": "Listing could not be saved",
            }

        matches = find_matches(extracted)

        sent_alerts = []

        for buyer in matches:
            buyer_phone = buyer.get("phone")

            if not buyer_phone:
                print("Skipping buyer with no phone:", buyer)
                continue

            deal = create_deal(
                listing_id=listing.get("id"),
                buyer=buyer,
            )

            if not deal:
                print("Deal could not be created for buyer:", buyer)
                continue

            buyer_message = f"""
 AGRI MATCH ALERT 

Commodity: {extracted.get('commodity')}
Quantity: {extracted.get('quantity')}
Location: {extracted.get('location')}

Deal ID: {deal.get('id')}

Reply YES if interested.
"""

            send_whatsapp_message(buyer_phone, buyer_message)

            sent_alerts.append({
                "buyer": buyer,
                "deal": deal,
            })

        return {
            "status": "saved",
            "listing": listing,
            "matches": matches,
            "alerts_sent": sent_alerts,
        }

    except Exception as e:
        print("Webhook error:", e)

        return {
            "status": "error",
            "message": str(e),
        }