from dotenv import load_dotenv
import os

# Load variables from the .env file into the program environment
load_dotenv()

print("CONFIG LOADED SUCCESSFULLY")
# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# WhatsApp Cloud API
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# Africa's Talking
AFRICASTALKING_API_KEY = os.getenv("AFRICASTALKING_API_KEY")
AFRICASTALKING_USERNAME = os.getenv("AFRICASTALKING_USERNAME")

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")
