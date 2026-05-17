import requests

from app.config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID


def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message,
        },
    }

    response = requests.post(url, headers=headers, json=payload)

    print("WhatsApp API Status:", response.status_code)
    print("WhatsApp API Response:", response.text)

    return response.json()


def send_whatsapp_buttons(to: str, body: str, buttons: list):
    url = f"https://graph.facebook.com/v25.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    formatted_buttons = []

    for button in buttons[:3]:
        formatted_buttons.append({
            "type": "reply",
            "reply": {
                "id": button["id"],
                "title": button["title"],
            },
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body,
            },
            "action": {
                "buttons": formatted_buttons,
            },
        },
    }

    response = requests.post(url, headers=headers, json=payload)

    print("WhatsApp Button API Status:", response.status_code)
    print("WhatsApp Button API Response:", response.text)

    return response.json()