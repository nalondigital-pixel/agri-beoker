from openai import OpenAI
from app.config import SAMBANOVA_API_KEY, SAMBANOVA_BASE_URL
from app.services.normalization_service import (
    apply_normalization,
    fallback_extract_market_data,
    log_unknown_term,
)
import json
import re

client = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url=SAMBANOVA_BASE_URL,
)


def extract_json_from_text(content: str):
    content = (content or "").strip()

    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, re.DOTALL)

    if match:
        return json.loads(match.group(0))

    return None


def extract_market_data(message: str):
    prompt = f"""
You are an AI extraction engine for an agricultural marketplace in Zimbabwe.

The user may write in English, Shona, Ndebele, slang, or mixed language.

Extract marketplace data from this message.

Message:
{message}

Return ONLY valid JSON with this schema:

{{
  "commodity": "",
  "quantity": 0,
  "location": "",
  "intent": "buy|sell|unknown",
  "confidence": 0.0,
  "possible_unknown_terms": []
}}

Rules:
- mombe means cattle
- mbudzi means goat
- huku means chicken
- chibage means maize
- If a word looks like a local/slang commodity but you are unsure, include it in possible_unknown_terms.
- Do not explain anything.
- Return JSON only.
"""

    try:
        response = client.chat.completions.create(
            model="Meta-Llama-3.3-70B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": "Return only valid JSON. No markdown. No explanation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content
        print("Raw AI Response:", repr(content))

        extracted = extract_json_from_text(content)

        if not extracted:
            print("AI returned invalid JSON. Using fallback extractor.")
            extracted = fallback_extract_market_data(message)

    except Exception as e:
        print("AI extractor failed. Using fallback extractor:", e)
        extracted = fallback_extract_market_data(message)

    # Log AI-suggested unknown terms for later admin approval
    possible_unknown_terms = extracted.get("possible_unknown_terms", [])

    if isinstance(possible_unknown_terms, list):
        for term in possible_unknown_terms:
            log_unknown_term(term, message)

    # Normalize AI output using dictionary + fallback
    extracted = apply_normalization(extracted, message)

    return extracted