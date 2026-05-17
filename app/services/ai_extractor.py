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
- unit: unit such as kg, bag, bags, crate, tonne, goat, cattle, bucket, dozen, or empty string if unknown
- location: town/area/location. If unknown, use empty string
- confidence: number from 0 to 1

Examples:
Message: "Ndine 20 kgs dze beef ku Rimuka Kadoma"
JSON: {{"intent":"sell","commodity":"beef","quantity":20,"unit":"kg","location":"Rimuka Kadoma","confidence":0.95}}

Message: "I want 10 bags maize in Chegutu"
JSON: {{"intent":"buy","commodity":"maize","quantity":10,"unit":"bags","location":"Chegutu","confidence":0.95}}

Message: "Looking for 4 goats near Kadoma"
JSON: {{"intent":"buy","commodity":"goat","quantity":4,"unit":"","location":"Kadoma","confidence":0.9}}

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


def normalize_extracted_payload(extracted: dict):
    if not extracted:
        return None

    intent = str(extracted.get("intent") or "unknown").lower().strip()

    if intent not in ["buy", "sell", "unknown"]:
        intent = "unknown"

    commodity = str(extracted.get("commodity") or "").lower().strip()
    unit = str(extracted.get("unit") or "").lower().strip()
    location = str(extracted.get("location") or "").lower().strip()

    try:
        quantity = float(extracted.get("quantity") or 0)

        if quantity.is_integer():
            quantity = int(quantity)

    except Exception:
        quantity = 0

    try:
        confidence = float(extracted.get("confidence") or 0.7)
    except Exception:
        confidence = 0.7

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

    print("Fallback Extracted:", fallback)

    return fallback