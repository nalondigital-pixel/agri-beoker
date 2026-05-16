from openai import OpenAI
from app.config import SAMBANOVA_API_KEY, SAMBANOVA_BASE_URL
import json
import re

client = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url=SAMBANOVA_BASE_URL,
)


def extract_market_data(message: str):
    prompt = f"""
You are an AI system for an agricultural marketplace in Zimbabwe.

Extract structured data from this message.

Return ONLY valid JSON.

Message:
{message}

Schema:
{{
  "commodity": "",
  "quantity": null,
  "location": "",
  "intent": "buy|sell|unknown",
  "confidence": 0.0
}}
"""

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

    # Raw text from the model
    content = (response.choices[0].message.content or "").strip()
    print("Raw AI Response:", repr(content))

    # If nothing came back, return a safe fallback
    if not content:
        return {
            "commodity": "unknown",
            "quantity": 0,
            "location": "unknown",
            "intent": "unknown",
            "confidence": 0.0,
            "raw": message
        }

    # Remove markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    # Try direct JSON parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting the first JSON object from the text
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    # Final fallback if parsing still fails
    return {
        "commodity": "unknown",
        "quantity": 0,
        "location": "unknown",
        "intent": "unknown",
        "confidence": 0.0,
        "raw": message,
        "model_output": content
    }