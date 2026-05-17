import json
import re

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.services.normalization_service import (
    fallback_extract_market_data,
    apply_normalization,
)


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["buy", "sell", "unknown"],
        },
        "commodity": {
            "type": "string",
        },
        "quantity": {
            "type": "number",
        },
        "unit": {
            "type": "string",
        },
        "location": {
            "type": "string",
        },
        "price": {
            "type": "number",
        },
        "currency": {
            "type": "string",
        },
        "price_per_unit": {
            "type": "number",
        },
        "transport_needed": {
            "type": "boolean",
        },
        "delivery_option": {
            "type": "string",
            "enum": [
                "can_deliver",
                "buyer_collects",
                "seller_delivers",
                "needs_transport",
                "will_collect",
                "unknown",
            ],
        },
        "transport_note": {
            "type": "string",
        },
        "confidence": {
            "type": "number",
        },
    },
    "required": [
        "intent",
        "commodity",
        "quantity",
        "unit",
        "location",
        "price",
        "currency",
        "price_per_unit",
        "transport_needed",
        "delivery_option",
        "transport_note",
        "confidence",
    ],
}


def clean_json_text(text: str):
    if not text:
        return None

    cleaned = text.strip()

    cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def get_gemini_client():
    if not GEMINI_API_KEY:
        return None

    return genai.Client(api_key=GEMINI_API_KEY)


def extract_with_gemini(message: str):
    client = get_gemini_client()

    if not client:
        return None

    prompt = f"""
You are an agricultural marketplace extraction engine for Zimbabwe.

Extract structured market data from this WhatsApp message.

The user may write in English, Shona, Ndebele, slang, or mixed language.

Return only JSON with these fields:
- intent: buy, sell, or unknown
- commodity: normalized English commodity name, singular where possible
- quantity: numeric quantity only. If unknown, use 0.
- unit: kg, bag, bags, crate, tonne, goat, cattle, bucket, dozen, or empty string if unknown
- location: town/area/location. If unknown, use empty string
- price: total price mentioned. If no price is mentioned, use 0.
- currency: USD, ZIG, ZAR, or empty string if unknown. In Zimbabwe, "$" usually means USD.
- price_per_unit: price divided by quantity when possible. If user says "$6 per bag", price_per_unit is 6.
- transport_needed: true if the user says they need transport/delivery help. Otherwise false.
- delivery_option:
  - can_deliver if seller says they can deliver
  - buyer_collects if seller says buyer must collect
  - seller_delivers if seller says delivery included
  - needs_transport if user needs transport
  - will_collect if buyer says they will collect
  - unknown if not mentioned
- transport_note: short transport/delivery note from the message, or empty string
- confidence: number from 0 to 1

Important:
- Do not confuse quantity with price.
- If message says "20 kg beef for $80", quantity is 20, price is 80, price_per_unit is 4.
- If message says "$6 per bag", price_per_unit is 6.
- If message says "budget $25", treat price as 25.
- If no price exists, price must be 0 and price_per_unit must be 0.
- If no transport info exists, transport_needed false, delivery_option unknown, transport_note empty.

Examples:
Message: "Ndine 20 kgs dze beef ku Rimuka Kadoma for $80 can deliver"
JSON: {{"intent":"sell","commodity":"beef","quantity":20,"unit":"kg","location":"Rimuka Kadoma","price":80,"currency":"USD","price_per_unit":4,"transport_needed":false,"delivery_option":"can_deliver","transport_note":"seller can deliver","confidence":0.95}}

Message: "I want 10 bags maize in Chegutu budget $60 need transport"
JSON: {{"intent":"buy","commodity":"maize","quantity":10,"unit":"bags","location":"Chegutu","price":60,"currency":"USD","price_per_unit":6,"transport_needed":true,"delivery_option":"needs_transport","transport_note":"buyer needs transport","confidence":0.95}}

Message: "Selling maize Chegutu $6 per bag buyer collects"
JSON: {{"intent":"sell","commodity":"maize","quantity":0,"unit":"bags","location":"Chegutu","price":0,"currency":"USD","price_per_unit":6,"transport_needed":false,"delivery_option":"buyer_collects","transport_note":"buyer collects","confidence":0.9}}

Message: "Ngifuna 4 goats eKadoma"
JSON: {{"intent":"buy","commodity":"goat","quantity":4,"unit":"","location":"Kadoma","price":0,"currency":"","price_per_unit":0,"transport_needed":false,"delivery_option":"unknown","transport_note":"","confidence":0.9}}

Message:
{message}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EXTRACTION_SCHEMA,
                temperature=0,
            ),
        )

        extracted = clean_json_text(response.text)

        if not extracted:
            print("Gemini returned non-JSON:", response.text)
            return None

        return extracted

    except Exception as e:
        print("Gemini extraction error:", e)
        return None


def safe_float(value, default=0):
    try:
        number = float(value or 0)

        if number.is_integer():
            return int(number)

        return round(number, 2)

    except Exception:
        return default


def normalize_extracted_payload(extracted: dict):
    if not extracted:
        return None

    intent = str(extracted.get("intent") or "unknown").lower().strip()

    if intent not in ["buy", "sell", "unknown"]:
        intent = "unknown"

    commodity = str(extracted.get("commodity") or "").lower().strip()
    unit = str(extracted.get("unit") or "").lower().strip()
    location = str(extracted.get("location") or "").lower().strip()

    quantity = safe_float(extracted.get("quantity"), 0)
    price = safe_float(extracted.get("price"), 0)
    price_per_unit = safe_float(extracted.get("price_per_unit"), 0)

    currency = str(extracted.get("currency") or "").upper().strip()

    if currency in ["$", "US$", "USDOLLAR", "USDOLLARS"]:
        currency = "USD"

    if price and not currency:
        currency = "USD"

    if price and quantity and not price_per_unit:
        price_per_unit = round(float(price) / float(quantity), 2)

    delivery_option = str(extracted.get("delivery_option") or "unknown").lower().strip()

    if delivery_option not in [
        "can_deliver",
        "buyer_collects",
        "seller_delivers",
        "needs_transport",
        "will_collect",
        "unknown",
    ]:
        delivery_option = "unknown"

    confidence = safe_float(extracted.get("confidence"), 0.7)

    if confidence < 0:
        confidence = 0

    if confidence > 1:
        confidence = 1

    return {
        "type": "listing",
        "intent": intent,
        "commodity": commodity,
        "quantity": quantity,
        "unit": unit,
        "raw_quantity_text": f"{quantity} {unit}".strip() if quantity else "",
        "location": location,
        "price": price if price else None,
        "currency": currency or None,
        "price_per_unit": price_per_unit if price_per_unit else None,
        "transport_needed": bool(extracted.get("transport_needed") or False),
        "delivery_option": delivery_option,
        "transport_note": str(extracted.get("transport_note") or "").strip(),
        "confidence": confidence,
    }


def extract_market_data(message: str, reporter_phone: str | None = None):
    gemini_result = extract_with_gemini(message)
    normalized_gemini = normalize_extracted_payload(gemini_result)

    if normalized_gemini:
        extracted = apply_normalization(
            normalized_gemini,
            message,
            reporter_phone=reporter_phone,
        )

        print("Gemini Extracted:", extracted)

        return extracted

    fallback = fallback_extract_market_data(
        message,
        reporter_phone=reporter_phone,
    )

    fallback = apply_normalization(
        fallback,
        message,
        reporter_phone=reporter_phone,
    )

    fallback["price"] = None
    fallback["currency"] = None
    fallback["price_per_unit"] = None
    fallback["transport_needed"] = False
    fallback["delivery_option"] = "unknown"
    fallback["transport_note"] = ""

    print("Fallback Extracted:", fallback)

    return fallback