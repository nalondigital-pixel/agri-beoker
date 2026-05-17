from app.services.session_service import get_session, set_session, clear_session
from app.services.profile_service import update_profile


LANGUAGE_OPTIONS = {
    "1": "english",
    "english": "english",
    "eng": "english",

    "2": "shona",
    "shona": "shona",
    "chishona": "shona",

    "3": "ndebele",
    "ndebele": "ndebele",
    "isindebele": "ndebele",
}


LANGUAGE_PROMPT = """
Welcome to Agri Broker 👋

Choose your language:

English
Shona
Ndebele
"""


NAME_PROMPTS = {
    "english": "Great. What is your name?",
    "shona": "Zvakanaka. Munonzi ani?",
    "ndebele": "Kulungile. Ungubani igama lakho?",
}


CITY_PROMPTS = {
    "english": "Which city/town are you in?\n\nExample: Kadoma",
    "shona": "Muri kuguta kana town ipi?\n\nSemuenzaniso: Kadoma",
    "ndebele": "Ukuliphi idolobho/town?\n\nIsibonelo: Kadoma",
}


AREA_PROMPTS = {
    "english": "Which area/neighborhood?\n\nExample: Rimuka",
    "shona": "Muri kuarea/neighborhood ipi?\n\nSemuenzaniso: Rimuka",
    "ndebele": "Ukweyiphi indawo/neighborhood?\n\nIsibonelo: Rimuka",
}


RULES_TEXT = {
    "english": """
Before you continue, please agree to these rules:

1. Be honest about what you are buying or selling.
2. Do not scam, threaten, or mislead other users.
3. Only share real produce/livestock requests.
4. Agri Broker may reduce trust points or block users who abuse the system.

Tap Agree to continue.
""",
    "shona": """
Musati maenderera mberi, bvumiranai nemitemo iyi:

1. Taurai chokwadi pane zvamuri kutenga kana kutengesa.
2. Musabire, kutyisidzira, kana kunyengera vamwe.
3. Shandisai system pazvinhu zvechokwadi zvekurima/zvipfuyo.
4. Agri Broker inogona kuderedza trust points kana kuvhara vanotyora mitemo.

Dzvanyai Agree kuti muenderere mberi.
""",
    "ndebele": """
Ungakaqhubeki, sicela uvumelane lemithetho le:

1. Khuluma iqiniso ngalokho okuthengayo kumbe okuthengisayo.
2. Ungaqili, ungesabisi, ungadukisi abanye.
3. Sebenzisa system ngezicelo zeqiniso zokulima/izifuyo.
4. Agri Broker inganciphisa ama trust points kumbe ivale abasebenzisa kabi system.

Cindezela Agree ukuze uqhubeke.
""",
}


DONE_MESSAGES = {
    "english": "✅ Registration complete, {name}.\n\nYou can now use the menu to buy, sell, or check deals.",
    "shona": "✅ Wapedza kunyoresa, {name}.\n\nIye zvino munogona kushandisa menu kutenga, kutengesa, kana kuona madeals.",
    "ndebele": "✅ Usuqedile ukubhalisa, {name}.\n\nManje usungasebenzisa i-menu ukuthenga, ukuthengisa, kumbe ukubona ama-deals.",
}


def normalize_language(message: str):
    if not message:
        return None

    key = message.strip().lower()
    return LANGUAGE_OPTIONS.get(key)


def handle_registration_message(phone: str, message: str):
    session = get_session(phone)

    if not session:
        set_session(phone, "choose_language", {})
        return LANGUAGE_PROMPT

    current_step = session.get("current_step")
    temp_data = session.get("temp_data") or {}

    if current_step == "choose_language":
        language = normalize_language(message)

        if not language:
            return LANGUAGE_PROMPT

        temp_data["language"] = language
        set_session(phone, "enter_name", temp_data)

        return NAME_PROMPTS.get(language, NAME_PROMPTS["english"])

    if current_step == "enter_name":
        name = message.strip()

        if len(name) < 2:
            language = temp_data.get("language", "english")
            return NAME_PROMPTS.get(language, NAME_PROMPTS["english"])

        temp_data["name"] = name
        set_session(phone, "enter_city", temp_data)

        language = temp_data.get("language", "english")
        return CITY_PROMPTS.get(language, CITY_PROMPTS["english"])

    if current_step == "enter_city":
        city = message.strip()

        if len(city) < 2:
            language = temp_data.get("language", "english")
            return CITY_PROMPTS.get(language, CITY_PROMPTS["english"])

        temp_data["city"] = city
        set_session(phone, "enter_area", temp_data)

        language = temp_data.get("language", "english")
        return AREA_PROMPTS.get(language, AREA_PROMPTS["english"])

    if current_step == "enter_area":
        neighborhood = message.strip()

        if len(neighborhood) < 2:
            language = temp_data.get("language", "english")
            return AREA_PROMPTS.get(language, AREA_PROMPTS["english"])

        temp_data["neighborhood"] = neighborhood
        set_session(phone, "agree_terms", temp_data)

        return "__SHOW_RULES_AGREE_BUTTON__"

    if current_step == "agree_terms":
        normalized = message.strip().lower()

        if normalized not in ["agree", "registration_agree_terms", "yes", "1"]:
            return "__SHOW_RULES_AGREE_BUTTON__"

        language = temp_data.get("language", "english")
        name = temp_data.get("name", "User")
        city = temp_data.get("city")
        neighborhood = temp_data.get("neighborhood")

        update_profile(phone, {
            "name": name,
            "language": language,
            "role": "both",
            "city": city,
            "neighborhood": neighborhood,
            "agreed_terms": True,
            "trust_score": 25,
            "trust_rank": "New User",
            "daily_tokens": 3,
            "free_daily_tokens": 3,
        })

        clear_session(phone)

        return DONE_MESSAGES.get(language, DONE_MESSAGES["english"]).format(name=name)

    clear_session(phone)
    set_session(phone, "choose_language", {})
    return LANGUAGE_PROMPT


def get_rules_text(language: str):
    return RULES_TEXT.get(language, RULES_TEXT["english"])