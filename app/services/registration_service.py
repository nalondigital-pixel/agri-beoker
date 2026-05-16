from app.services.profile_service import create_or_update_profile
from app.services.session_service import get_session, set_session, clear_session


LANGUAGE_PROMPT = """
🌍 Choose your language / Shandura mutauro / Khetha ulimi

1. English
2. Shona
3. Ndebele
"""

NAME_PROMPTS = {
    "english": "👤 What is your name?",
    "shona": "👤 Zita renyu ndiani?",
    "ndebele": "👤 Ungubani ibizo lakho?",
}

ROLE_PROMPTS = {
    "english": """
Hi {name}. What do you want to do?

💵 1. Buy
🐄 2. Sell
🔁 3. Both
""",
    "shona": """
Mhoroi {name}. Munoda kuita chii?

💵 1. Kutenga
🐄 2. Kutengesa
🔁 3. Zvese
""",
    "ndebele": """
Sawubona {name}. Ufuna ukwenzani?

💵 1. Ukuthenga
🐄 2. Ukuthengisa
🔁 3. Kokubili
""",
}

LOCATION_PROMPTS = {
    "english": "📍 Send your city and neighborhood. Example: Kadoma, Rimuka",
    "shona": "📍 Tumira guta nenzvimbo. Semuenzaniso: Kadoma, Rimuka",
    "ndebele": "📍 Thumela idolobho lendawo. Isibonelo: Kadoma, Rimuka",
}

AGREE_PROMPTS = {
    "english": """
🛡️ Community safety rules:
- No fake listings
- No ghosting buyers/sellers
- No fraud
- Respect all users

Type AGREE to continue.
""",
    "shona": """
🛡️ Mitemo yekuchengetedzana:
- Hapana fake listings
- Usanyangarika pa deal
- Hapana chitsotsi
- Remekedza vamwe

Nyora AGREE kuti uenderere mberi.
""",
    "ndebele": """
🛡️ Imithetho yokuphepha:
- Akula ma fake listings
- Unganyamalali ku deal
- Akula ubuqili
- Hlonipha abanye

Bhala AGREE ukuze uqhubeke.
""",
}

DONE_MESSAGES = {
    "english": """
✅ Registration complete, {name}.

You now have 3 free daily listing tokens.

You can send:
"Ndine 4 mbudzi ku Kadoma"
""",
    "shona": """
✅ Wapedza kunyoresa, {name}.

Une 3 free daily listing tokens.

Unogona kutumira:
"Ndine 4 mbudzi ku Kadoma"
""",
    "ndebele": """
✅ Usuqedile ukubhalisa, {name}.

Ule 3 free daily listing tokens.

Ungathumela:
"Ndine 4 mbudzi ku Kadoma"
""",
}


def normalize_language(choice: str):
    choice = choice.strip()

    if choice == "1":
        return "english"

    if choice == "2":
        return "shona"

    if choice == "3":
        return "ndebele"

    return None


def normalize_role(choice: str):
    choice = choice.strip()

    if choice == "1":
        return "buyer"

    if choice == "2":
        return "seller"

    if choice == "3":
        return "both"

    return None


def start_registration(phone: str):
    set_session(phone, "choose_language", {})
    return LANGUAGE_PROMPT


def handle_registration_message(phone: str, message: str):
    session = get_session(phone)

    if not session:
        return start_registration(phone)

    step = session.get("current_step")
    temp_data = session.get("temp_data") or {}
    message_clean = message.strip()

    if step == "choose_language":
        language = normalize_language(message_clean)

        if not language:
            return LANGUAGE_PROMPT

        temp_data["language"] = language
        set_session(phone, "enter_name", temp_data)

        return NAME_PROMPTS[language]

    if step == "enter_name":
        language = temp_data.get("language", "english")
        name = message_clean.strip()

        if len(name) < 2:
            return NAME_PROMPTS[language]

        temp_data["name"] = name
        set_session(phone, "choose_role", temp_data)

        return ROLE_PROMPTS[language].format(name=name)

    if step == "choose_role":
        language = temp_data.get("language", "english")
        role = normalize_role(message_clean)

        if not role:
            return ROLE_PROMPTS[language].format(
                name=temp_data.get("name", "")
            )

        temp_data["role"] = role
        set_session(phone, "enter_location", temp_data)

        return LOCATION_PROMPTS[language]

    if step == "enter_location":
        language = temp_data.get("language", "english")

        if "," in message_clean:
            city, neighborhood = [part.strip() for part in message_clean.split(",", 1)]
        else:
            city = message_clean
            neighborhood = ""

        temp_data["city"] = city
        temp_data["neighborhood"] = neighborhood

        set_session(phone, "agree_terms", temp_data)

        return AGREE_PROMPTS[language]

    if step == "agree_terms":
        language = temp_data.get("language", "english")

        if message_clean.upper() != "AGREE":
            return AGREE_PROMPTS[language]

        create_or_update_profile(phone, {
            "name": temp_data.get("name"),
            "language": temp_data.get("language"),
            "role": temp_data.get("role"),
            "city": temp_data.get("city"),
            "neighborhood": temp_data.get("neighborhood"),
            "agreed_terms": True,
            "free_daily_tokens": 3,
            "ghost_match_strikes": 0,
            "verified": False,
            "reputation": 0,
        })

        clear_session(phone)

        return DONE_MESSAGES[language].format(
            name=temp_data.get("name", "")
        )

    return start_registration(phone)