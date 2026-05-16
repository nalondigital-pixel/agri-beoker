import os
import requests


AFRICASTALKING_API_KEY = os.getenv("AT_API_KEY")
AFRICASTALKING_USERNAME = os.getenv("AT_USERNAME")


def send_sms(phone, message):
    """
    Send SMS to buyer or seller (fallback communication layer)
    """

    url = "https://api.africastalking.com/version1/messaging"

    headers = {
        "apiKey": AFRICASTALKING_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    payload = {
        "username": AFRICASTALKING_USERNAME,
        "to": phone,
        "message": message
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        return response.json()

    except Exception as e:
        print("SMS Error:", e)
        return None