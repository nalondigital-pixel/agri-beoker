from google import genai

from app.config import GEMINI_API_KEY, GEMINI_MODEL


def get_gemini_client():
    if not GEMINI_API_KEY:
        return None

    return genai.Client(api_key=GEMINI_API_KEY)


def generate_ai_assistant_reply(
    user_message: str,
    user_name: str | None = None,
    user_language: str | None = None,
):
    client = get_gemini_client()

    if not client:
        return (
            "I can help you buy or sell agricultural products.\n\n"
            "Use the buttons below to continue."
        )

    name_text = user_name or "the user"
    language_text = user_language or "English"

    prompt = f"""
You are Agri Broker, an AI WhatsApp agricultural marketplace assistant in Zimbabwe.

Your job:
- Help farmers, buyers, sellers, butcheries, transporters, and agro-dealers.
- Explain how the marketplace works.
- Guide users to create buy or sell requests.
- Support English, Shona, and Ndebele style conversations.
- Keep answers short because this is WhatsApp.
- Be friendly, practical, and business-like.
- Never pretend a deal is confirmed unless the system confirms it.
- Never promise payment handling, delivery, escrow, or guarantees.
- Warn users not to send deposits before verifying goods.
- If the user wants to buy, guide them to tap Buy.
- If the user wants to sell, guide them to tap Sell.
- If the user asks about their deals, guide them to tap My Deals.
- If the user sends an incomplete listing, tell them the correct format.

User name: {name_text}
Preferred language: {language_text}

Good listing examples:
- 20 kg beef in Rimuka Kadoma for $80
- I want 10 bags maize in Chegutu budget $60
- Selling 4 goats in Kadoma $45 each
- Ndine 3 mombe ku Chegutu
- Ngifuna 20kg potatoes eBulawayo

Important:
Keep the reply under 700 characters.
Do not use markdown tables.
Do not output JSON.
Do not mention Gemini or AI model names.

User message:
{user_message}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        reply = (response.text or "").strip()

        if not reply:
            return (
                "I can help you buy or sell agricultural products.\n\n"
                "Tap Buy if you are looking for goods, or Sell if you have goods available."
            )

        if len(reply) > 900:
            reply = reply[:900].strip() + "..."

        return reply

    except Exception as e:
        print("AI assistant error:", e)

        return (
            "I can help you buy or sell agricultural products.\n\n"
            "Tap Buy if you are looking for goods, or Sell if you have goods available."
        )