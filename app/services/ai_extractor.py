import json
import re

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.services.normalization_service import (
    fallback_extract_market_data,
    apply_normalization,
)
from app.services.location_normalizer_service import (
    normalize_location_name,
    best_location,
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


def preprocess_user_message(message: str):
    """
    Makes farmer/user messages easier to extract.

    Handles:
    - 16kgs -> 16 kgs
    - 16KG -> 16 kg
    - 20bags -> 20 bags
    - 5boxes -> 5 boxes
    - 3goats -> 3 goats
    - $5abox -> $5 a box
    - beef16kgs -> beef 16 kgs
    - kuchegut -> ku chegut
    - mixed case
    """

    if not message:
        return ""

    text = str(message).strip()

    # Normalize common unicode punctuation.
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')

    # Add space between a number and letters: 16kgs -> 16 kgs
    text = re.sub(r"(\d+)([a-zA-Z]+)", r"\1 \2", text)

    # Add space between letters and a following number: beef16 -> beef 16
    text = re.sub(r"([a-zA-Z])(\d+)", r"\1 \2", text)

    # Add space between letter and money symbol: box$5 -> box $5
    text = re.sub(r"([a-zA-Z])(\$)", r"\1 \2", text)

    # Normalize compact currency plus unit: $80kg -> $80 kg
    text = re.sub(r"(\$\s*\d+(?:\.\d+)?)([a-zA-Z]+)", r"\1 \2", text)

    # Normalize "$5abox" / "$5 a box" style.
    text = re.sub(
        r"\ba\s*(kg|kgs|bag|bags|box|boxes|crate|crates|bucket|buckets|goat|goats)\b",
        r"a \1",
        text,
        flags=re.IGNORECASE,
    )

    # Normalize common joined Shona/location fragments:
    # kuchegut -> ku chegut, mukadma -> mu kadma, pahararre -> pa hararre
    text = re.sub(r"\bku([a-zA-Z]{4,})\b", r"ku \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmu([a-zA-Z]{4,})\b", r"mu \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bpa([a-zA-Z]{4,})\b", r"pa \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\be([a-zA-Z]{4,})\b", r"e \1", text, flags=re.IGNORECASE)

    # Normalize repeated whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


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

    cleaned_message = preprocess_user_message(message)

    prompt = f"""
You are an agricultural marketplace extraction engine for Zimbabwe.

Extract structured market data from this WhatsApp message.

The user may write in English, Shona, Ndebele, slang, mixed language, bad spelling, no spaces, or mixed case.

Return only JSON with these fields:
- intent: buy, sell, or unknown
- commodity: normalized English commodity name, singular where possible
- quantity: numeric quantity only. If unknown, use 0.
- unit: kg, kgs, bag, bags, box, boxes, crate, crates, tonne, tonnes, goat, goats, cattle, bucket, buckets, dozen, or empty string if unknown
- location: Zimbabwe town/area/location. If unknown, use empty string.
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

Important quantity rules:
- Treat "16kgs", "16kg", "16 kgs", "16 KG", and "16KGS" as quantity 16 and unit kg.
- Treat "20bags" as quantity 20 and unit bags.
- Treat "5boxes" as quantity 5 and unit boxes.
- Treat "3goats" as quantity 3 and commodity goat unless goats are clearly the unit.
- Do not confuse quantity with price.
- If message says "20 kg beef for $80", quantity is 20, price is 80, price_per_unit is 4.
- If message says "$6 per bag", price_per_unit is 6.
- If message says "budget $25", treat price as 25.
- If no price exists, price must be 0 and price_per_unit must be 0.
- If no transport info exists, transport_needed false, delivery_option unknown, transport_note empty.

Important location rules:
- Zimbabwe town/location spelling may be wrong.
- "chegut", "chegu", "chegto" likely means Chegutu.
- "kadma", "kadom" likely means Kadoma.
- "hararre", "harar", "hre" likely means Harare.
- "bulwayo", "byo" likely means Bulawayo.
- "kwkwe" likely means Kwekwe.
- "chitungiza" likely means Chitungwiza.
- If the user says "rimuka kadma", location should be Rimuka Kadoma.
- If the user says "ku chegut", location should be Chegutu.
- If the user says "near hararre", location should be Harare.
- If location is unclear, return your best Zimbabwe location guess with lower confidence.

Examples:
Message: "16kgs beef kadoma"
JSON: {{"intent":"unknown","commodity":"beef","quantity":16,"unit":"kg","location":"Kadoma","price":0,"currency":"","price_per_unit":0,"transport_needed":false,"delivery_option":"unknown","transport_note":"","confidence":0.9}}

Message: "Ndine 20kgs dze beef ku Rimuka Kadoma for $80 can deliver"
JSON: {{"intent":"sell","commodity":"beef","quantity":20,"unit":"kg","location":"Rimuka Kadoma","price":80,"currency":"USD","price_per_unit":4,"transport_needed":false,"delivery_option":"can_deliver","transport_note":"seller can deliver","confidence":0.95}}

Message: "I want 10bags maize in Chegutu budget $60 need transport"
JSON: {{"intent":"buy","commodity":"maize","quantity":10,"unit":"bags","location":"Chegutu","price":60,"currency":"USD","price_per_unit":6,"transport_needed":true,"delivery_option":"needs_transport","transport_note":"buyer needs transport","confidence":0.95}}

Message: "Selling maize Chegutu $6 per bag buyer collects"
JSON: {{"intent":"sell","commodity":"maize","quantity":0,"unit":"bags","location":"Chegutu","price":0,"currency":"USD","price_per_unit":6,"transport_needed":false,"delivery_option":"buyer_collects","transport_note":"buyer collects","confidence":0.9}}

Message: "Ngifuna 4goats eKadoma"
JSON: {{"intent":"buy","commodity":"goat","quantity":4,"unit":"","location":"Kadoma","price":0,"currency":"","price_per_unit":0,"transport_needed":false,"delivery_option":"unknown","transport_note":"","confidence":0.9}}

Message: "16kgs beef ku chegut"
JSON: {{"intent":"unknown","commodity":"beef","quantity":16,"unit":"kg","location":"Chegutu","price":0,"currency":"","price_per_unit":0,"transport_needed":false,"delivery_option":"unknown","transport_note":"","confidence":0.9}}

Message: "20bags maize near hararre"
JSON: {{"intent":"unknown","commodity":"maize","quantity":20,"unit":"bags","location":"Harare","price":0,"currency":"","price_per_unit":0,"transport_needed":false,"delivery_option":"unknown","transport_note":"","confidence":0.9}}

Message: "5boxes tomatoes rimuka kadma"
JSON: {{"intent":"unknown","commodity":"tomato","quantity":5,"unit":"boxes","location":"Rimuka Kadoma","price":0,"currency":"","price_per_unit":0,"transport_needed":false,"delivery_option":"unknown","transport_note":"","confidence":0.9}}

Original message:
{message}

Cleaned message:
{cleaned_message}
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


def normalize_unit(unit: str):
    unit = str(unit or "").lower().strip()

    unit_map = {
        "kgs": "kg",
        "kg": "kg",
        "kilogram": "kg",
        "kilograms": "kg",
        "kilo": "kg",
        "kilos": "kg",

        "bag": "bags",
        "bags": "bags",

        "box": "boxes",
        "boxes": "boxes",

        "crate": "crates",
        "crates": "crates",

        "bucket": "buckets",
        "buckets": "buckets",

        "ton": "tonnes",
        "tons": "tonnes",
        "tonne": "tonnes",
        "tonnes": "tonnes",

        # Animals are usually commodity/count, not unit.
        "goat": "",
        "goats": "",
        "cattle": "",
        "cow": "",
        "cows": "",
        "chicken": "",
        "chickens": "",
    }

    return unit_map.get(unit, unit)


def normalize_currency(currency: str):
    currency = str(currency or "").upper().strip()

    if currency in ["$", "US$", "USDOLLAR", "USDOLLARS", "US"]:
        return "USD"

    if currency in ["RTGS", "ZWL", "ZIG"]:
        return "ZIG"

    if currency in ["RAND", "RANDS", "ZAR", "R"]:
        return "ZAR"

    return currency


def normalize_extracted_payload(extracted: dict):
    if not extracted:
        return None

    intent = str(extracted.get("intent") or "unknown").lower().strip()

    if intent not in ["buy", "sell", "unknown"]:
        intent = "unknown"

    commodity = str(extracted.get("commodity") or "").lower().strip()
    unit = normalize_unit(extracted.get("unit"))

    # Normalize whatever Gemini returns, but final correction using the whole
    # message is done inside extract_market_data().
    location = normalize_location_name(extracted.get("location") or "")

    quantity = safe_float(extracted.get("quantity"), 0)
    price = safe_float(extracted.get("price"), 0)
    price_per_unit = safe_float(extracted.get("price_per_unit"), 0)

    currency = normalize_currency(extracted.get("currency"))

    if price and not currency:
        currency = "USD"

    if price and quantity and not price_per_unit:
        try:
            price_per_unit = round(float(price) / float(quantity), 2)
        except Exception:
            price_per_unit = 0

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
    cleaned_message = preprocess_user_message(message)

    gemini_result = extract_with_gemini(cleaned_message)
    normalized_gemini = normalize_extracted_payload(gemini_result)

    if normalized_gemini:
        extracted = apply_normalization(
            normalized_gemini,
            cleaned_message,
            reporter_phone=reporter_phone,
        )

        # Important:
        # This scans the full message too, so typos like "chegut" still work
        # even if Gemini/fallback left location blank.
        extracted["location"] = best_location(
            extracted.get("location") or "",
            cleaned_message,
        )

        print("Original Message:", message)
        print("Cleaned Message:", cleaned_message)
        print("Gemini Raw:", gemini_result)
        print("Gemini Extracted:", extracted)

        return extracted

    fallback = fallback_extract_market_data(
        cleaned_message,
        reporter_phone=reporter_phone,
    )

    fallback = apply_normalization(
        fallback,
        cleaned_message,
        reporter_phone=reporter_phone,
    )

    fallback["location"] = best_location(
        fallback.get("location") or "",
        cleaned_message,
    )

    fallback["price"] = None
    fallback["currency"] = None
    fallback["price_per_unit"] = None
    fallback["transport_needed"] = False
    fallback["delivery_option"] = "unknown"
    fallback["transport_note"] = ""

    print("Original Message:", message)
    print("Cleaned Message:", cleaned_message)
    print("Fallback Extracted:", fallback)

    return fallback