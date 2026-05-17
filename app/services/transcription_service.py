from openai import OpenAI

from app.config import SAMBANOVA_API_KEY, SAMBANOVA_BASE_URL


client = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url=SAMBANOVA_BASE_URL,
)


def transcribe_audio(file_path: str):
    """
    Placeholder for now.

    Important:
    SambaNova chat API may not support audio transcription directly.
    So this is where we will later connect:
    - OpenAI Whisper
    - local Whisper
    - Groq Whisper
    - another transcription API

    For now, we return None so voice messages do not break the app.
    """

    print("Voice note received, but transcription provider is not connected yet.")
    print("Audio saved at:", file_path)

    return None