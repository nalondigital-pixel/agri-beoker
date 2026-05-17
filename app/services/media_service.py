import requests

from app.config import WHATSAPP_ACCESS_TOKEN


def get_media_url(media_id: str):
    url = f"https://graph.facebook.com/v25.0/{media_id}"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    }

    response = requests.get(url, headers=headers)

    print("Media URL Status:", response.status_code)
    print("Media URL Response:", response.text)

    data = response.json()
    return data.get("url")


def download_media(media_url: str, output_path: str):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    }

    response = requests.get(media_url, headers=headers)

    print("Download Media Status:", response.status_code)

    with open(output_path, "wb") as file:
        file.write(response.content)

    return output_path