import re

from app.services.session_service import get_session, set_session, clear_session
from app.services.transporter_service import register_or_update_transporter
from app.services.location_normalizer_service import normalize_location_name


TRANSPORTER_COMMANDS = [
    "transporter",
    "driver",
    "truck",
    "lorry",
    "i am a transporter",
    "i am transporter",
    "register transporter",
    "register as transporter",
    "transport registration",
    "transport",
]


def is_transporter_registration_command(message: str):
    if not message:
        return False

    text = str(message).strip().lower()

    return text in TRANSPORTER_COMMANDS


def start_transporter_registration(phone: str):
    set_session(
        phone,
        "transporter_registration",
        {
            "step": "name",
            "data": {},
        },
    )

    return {
        "handled": True,
        "done": False,
        "reply": (
            "🚛 Transporter Registration\n\n"
            "Great. I will register you as a transporter.\n\n"
            "You can type *cancel* anytime to stop.\n\n"
            "What is your name or company name?"
        ),
        "buttons": None,
    }


def parse_capacity(message: str):
    """
    Examples:
    - 1000kg
    - 1000 kg
    - 1 tonne
    - 2 tonnes
    - 50 boxes
    - 100 bags
    """

    text = str(message or "").lower().strip()

    text = text.replace(",", "")
    text = re.sub(r"(\d+)([a-zA-Z]+)", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text).strip()

    number_match = re.search(r"(\d+(?:\.\d+)?)", text)

    if not number_match:
        return None, None

    value = float(number_match.group(1))

    if value.is_integer():
        value = int(value)

    unit = "kg"

    if "tonne" in text or "tonnes" in text or "ton" in text or "tons" in text:
        unit = "tonnes"

    elif "box" in text or "boxes" in text:
        unit = "boxes"

    elif "bag" in text or "bags" in text:
        unit = "bags"

    elif "kg" in text or "kgs" in text or "kilogram" in text or "kilograms" in text:
        unit = "kg"

    return value, unit


def build_location_pin_prompt():
    return {
        "handled": True,
        "done": False,
        "reply": (
            "📍 Optional but recommended:\n\n"
            "Please send your WhatsApp live/current location pin so we can match you to nearby transport jobs.\n\n"
            "How to send location:\n"
            "1. Tap the paperclip / + icon\n"
            "2. Tap Location\n"
            "3. Send your current location\n\n"
            "Or tap *Skip Pin* if you want to continue without GPS."
        ),
        "buttons": [
            {
                "id": "transporter_skip_pin",
                "title": "Skip Pin",
            }
        ],
    }


def handle_transporter_location_pin(phone: str, location_pin: dict):
    """
    Called from whatsapp.py when user sends a location pin during transporter registration.
    """

    session = get_session(phone)

    if not session or session.get("current_step") != "transporter_registration":
        return {
            "handled": False,
        }

    temp_data = session.get("temp_data") or {}
    step = temp_data.get("step")
    data = temp_data.get("data") or {}

    if step != "location_pin":
        return {
            "handled": False,
        }

    data["latitude"] = location_pin.get("latitude")
    data["longitude"] = location_pin.get("longitude")

    pin_address = (
        location_pin.get("address")
        or location_pin.get("name")
        or data.get("base_location")
        or ""
    )

    if pin_address and not data.get("base_location"):
        data["base_location"] = normalize_location_name(pin_address)

    set_session(
        phone,
        "transporter_registration",
        {
            "step": "vehicle_type",
            "data": data,
        },
    )

    return {
        "handled": True,
        "done": False,
        "reply": (
            "✅ Transporter location pin saved.\n\n"
            "What vehicle do you use?\n\n"
            "Examples:\n"
            "pickup\n"
            "1 tonne truck\n"
            "3 tonne truck\n"
            "lorry\n"
            "kombi"
        ),
        "buttons": None,
    }


def handle_transporter_registration_message(phone: str, message: str):
    session = get_session(phone)

    if not session or session.get("current_step") != "transporter_registration":
        return {
            "handled": False,
        }

    temp_data = session.get("temp_data") or {}
    step = temp_data.get("step") or "name"
    data = temp_data.get("data") or {}

    text = str(message or "").strip()
    text_lower = text.lower()

    if text_lower in ["cancel", "stop", "quit"]:
        clear_session(phone)

        return {
            "handled": True,
            "done": False,
            "reply": (
                "Transporter registration cancelled.\n\n"
                "Send *transporter* anytime to start again."
            ),
            "buttons": None,
        }

    if step == "name":
        if len(text) < 2:
            return {
                "handled": True,
                "done": False,
                "reply": "Please send your name or company name.",
                "buttons": None,
            }

        data["name"] = text

        set_session(
            phone,
            "transporter_registration",
            {
                "step": "base_location",
                "data": data,
            },
        )

        return {
            "handled": True,
            "done": False,
            "reply": (
                "Which town or area are you based in?\n\n"
                "Examples:\n"
                "Harare\n"
                "Chegutu\n"
                "Kadoma\n"
                "Mutare\n"
                "Bulawayo"
            ),
            "buttons": None,
        }

    if step == "base_location":
        normalized_location = normalize_location_name(text)

        if not normalized_location:
            return {
                "handled": True,
                "done": False,
                "reply": (
                    "Please send your base town or area.\n\n"
                    "Example: Harare, Chegutu, Kadoma"
                ),
                "buttons": None,
            }

        data["base_location"] = normalized_location

        set_session(
            phone,
            "transporter_registration",
            {
                "step": "location_pin",
                "data": data,
            },
        )

        return build_location_pin_prompt()

    if step == "location_pin":
        if text_lower == "transporter_skip_pin" or text_lower in ["skip", "skip pin", "no"]:
            set_session(
                phone,
                "transporter_registration",
                {
                    "step": "vehicle_type",
                    "data": data,
                },
            )

            return {
                "handled": True,
                "done": False,
                "reply": (
                    "No problem. We will use your base town instead.\n\n"
                    "What vehicle do you use?\n\n"
                    "Examples:\n"
                    "pickup\n"
                    "1 tonne truck\n"
                    "3 tonne truck\n"
                    "lorry\n"
                    "kombi"
                ),
                "buttons": None,
            }

        return build_location_pin_prompt()

    if step == "vehicle_type":
        if len(text) < 2:
            return {
                "handled": True,
                "done": False,
                "reply": "Please send your vehicle type. Example: 1 tonne truck.",
                "buttons": None,
            }

        data["vehicle_type"] = text

        set_session(
            phone,
            "transporter_registration",
            {
                "step": "capacity",
                "data": data,
            },
        )

        return {
            "handled": True,
            "done": False,
            "reply": (
                "What load capacity can you carry?\n\n"
                "Examples:\n"
                "1000kg\n"
                "1 tonne\n"
                "50 boxes\n"
                "100 bags"
            ),
            "buttons": None,
        }

    if step == "capacity":
        capacity, unit = parse_capacity(text)

        if not capacity:
            return {
                "handled": True,
                "done": False,
                "reply": (
                    "I could not understand the capacity.\n\n"
                    "Please send something like:\n"
                    "1000kg\n"
                    "1 tonne\n"
                    "50 boxes\n"
                    "100 bags"
                ),
                "buttons": None,
            }

        data["vehicle_capacity"] = capacity
        data["capacity_unit"] = unit

        transporter = register_or_update_transporter(
            phone=phone,
            name=data.get("name"),
            base_location=data.get("base_location"),
            vehicle_type=data.get("vehicle_type"),
            vehicle_capacity=data.get("vehicle_capacity"),
            capacity_unit=data.get("capacity_unit"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            is_verified=False,
        )

        clear_session(phone)

        if not transporter:
            return {
                "handled": True,
                "done": False,
                "reply": (
                    "Sorry, I could not save your transporter registration. "
                    "Please try again later."
                ),
                "buttons": None,
            }

        gps_line = "GPS pin: saved" if data.get("latitude") and data.get("longitude") else "GPS pin: not provided"

        return {
            "handled": True,
            "done": True,
            "reply": (
                "✅ Transporter registration received.\n\n"
                f"Name: {data.get('name')}\n"
                f"Base: {data.get('base_location')}\n"
                f"Vehicle: {data.get('vehicle_type')}\n"
                f"Capacity: {data.get('vehicle_capacity')} {data.get('capacity_unit')}\n"
                f"{gps_line}\n\n"
                "Your transporter account is now pending verification.\n\n"
                "Once verified by admin, you can receive transport job alerts from Agri Broker."
            ),
            "buttons": None,
        }

    return {
        "handled": True,
        "done": False,
        "reply": "Please send the next transporter registration detail.",
        "buttons": None,
    }