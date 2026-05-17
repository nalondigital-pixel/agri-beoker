import os
import time

from google import genai

from app.config import GEMINI_API_KEY, GEMINI_MODEL


def get_gemini_client():
    if not GEMINI_API_KEY:
        return None

    return genai.Client(api_key=GEMINI_API_KEY)


def transcribe_audio(file_path: str):
    client = get_gemini_client()

    if not client:
        print("Gemini transcription skipped: missing GEMINI_API_KEY")
        return None

    if not file_path or not os.path.exists(file_path):
        print("Gemini transcription skipped: file not found")
        return None

    try:
        uploaded_file = client.files.upload(file=file_path)

        # Give Gemini a moment to process the uploaded audio.
        time.sleep(1)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                uploaded_file,
                (
                    "Transcribe this WhatsApp voice note. "
                    "The speaker may use English, Shona, Ndebele, or mixed language. "
                    "Return only the spoken text. Do not explain."
                ),
            ],
        )

        transcript = (response.text or "").strip()

        if not transcript:
            return None

        print("Gemini transcript:", transcript)

        return transcript

    except Exception as e:
        print("Gemini transcription error:", e)
        return None