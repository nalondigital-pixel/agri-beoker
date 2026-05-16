import requests

from app.config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID


def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    print("WHATSAPP URL:", url)
    print("PHONE_NUMBER_ID:", WHATSAPP_PHONE_NUMBER_ID)
    print("TOKEN LOADED:", WHATSAPP_ACCESS_TOKEN is not None)

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    response = requests.post(url, headers=headers, json=payload)

    print("WhatsApp API Status:", response.status_code)
    print("WhatsApp API Response:", response.text)

    return response.json()