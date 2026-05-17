import os
from dotenv import load_dotenv

load_dotenv()

# WhatsApp
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Old AI / optional
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")
SAMBANOVA_BASE_URL = os.getenv("SAMBANOVA_BASE_URL")

# Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Dashboard
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")

# Cron
CRON_SECRET = os.getenv("CRON_SECRET")