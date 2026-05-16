import re
from difflib import get_close_matches
from datetime import datetime, timezone

from app.db.supabase_client import supabase


AUTO_PROMOTE_COUNT_THRESHOLD = 5
AUTO_PROMOTE_UNIQUE_USERS_THRESHOLD = 3


COMMON_COMMODITIES = {
    # Livestock
    "mombe": "cattle",
    "cattle": "cattle",
    "cow": "cattle",
    "cows": "cattle",
    "bull": "cattle",
    "bulls": "cattle",
    "ox": "cattle",
    "oxen": "cattle",
    "heifer": "cattle",
    "calf": "cattle",

    "mbudzi": "goat",
    "goat": "goat",
    "goats": "goat",

    "hwai": "sheep",
    "sheep": "sheep",
    "ram": "sheep",
    "ewe": "sheep",
    "lamb": "sheep",

    "nguruve": "pig",
    "pig": "pig",
    "pigs": "pig",

    "huku": "chicken",
    "chicken": "chicken",
    "chickens": "chicken",
    "broiler": "chicken",
    "broilers": "chicken",
    "layer": "chicken",
    "layers": "chicken",
    "roadrunner": "chicken",
    "rabbit": "rabbit",
    "rabbits": "rabbit",

    # Meat
    "beef": "beef",
    "nyama": "meat",
    "meat": "meat",
    "pork": "pork",
    "mutton": "mutton",
    "tripe": "tripe",
    "matumbu": "tripe",
    "liver": "liver",

    # Grains
    "maize": "maize",
    "corn": "maize",
    "chibage": "maize",
    "mealies": "maize",
    "sorghum": "sorghum",
    "mapfunde": "sorghum",
    "millet": "millet",
    "mhunga": "pearl millet",
    "rapoko": "finger millet",
    "wheat": "wheat",
    "rice": "rice",

    # Legumes
    "beans": "beans",
    "bean": "beans",
    "nyemba": "beans",
    "cowpeas": "cowpeas",
    "nyimo": "bambara nuts",
    "groundnuts": "groundnuts",
    "nzungu": "groundnuts",
    "peanuts": "groundnuts",
    "soya": "soybeans",
    "soybeans": "soybeans",
    "soyabeans": "soybeans",

    # Vegetables
    "tomato": "tomato",
    "tomatoes": "tomato",
    "matomatisi": "tomato",
    "onion": "onion",
    "onions": "onion",
    "hanyanisi": "onion",
    "potato": "potato",
    "potatoes": "potato",
    "mbatatisi": "potato",
    "sweet potato": "sweet potato",
    "mbambaira": "sweet potato",
    "cabbage": "cabbage",
    "cabbages": "cabbage",
    "rape": "rape",
    "covo": "covo",
    "tsunga": "tsunga",
    "spinach": "spinach",
    "carrot": "carrot",
    "carrots": "carrot",
    "butternut": "butternut",
    "pumpkin": "pumpkin",
    "manhanga": "pumpkin",

    # Fruits
    "banana": "banana",
    "bananas": "banana",
    "orange": "orange",
    "oranges": "orange",
    "mango": "mango",
    "mangoes": "mango",
    "avocado": "avocado",
    "avocados": "avocado",
    "watermelon": "watermelon",

    # Dairy / eggs
    "milk": "milk",
    "eggs": "eggs",
    "egg": "eggs",
}


UNIT_ALIASES = {
    "bag": "bags",
    "bags": "bags",
    "sack": "bags",
    "sacks": "bags",

    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",

    "bucket": "buckets",
    "buckets": "buckets",
    "buckes": "buckets",

    "crate": "crates",
    "crates": "crates",

    "box": "boxes",
    "boxes": "boxes",

    "ton": "tons",
    "tons": "tons",
    "tonne": "tons",
    "tonnes": "tons",

    "dozen": "dozen",
    "dozens": "dozen",

    "head": "head",
    "heads": "head",
}


STOP_WORDS = {
    # English
    "i", "have", "has", "am", "is", "are", "selling", "sell", "buy",
    "available", "in", "at", "the", "a", "an", "with", "and", "for",
    "to", "of", "from",

    # Shona / Ndebele fillers
    "ndine", "ndiri", "tine", "pane", "ku", "mu", "pa", "dze", "dzangu",
    "dza", "dze", "ye", "yema", "re", "ra", "e", "ze", "za", "zve", "zva",
    "che", "cha", "chemu", "yeku", "dzeku", "zvekutengesa", "dzinotengeswa",

    # Units
    *UNIT_ALIASES.keys(),
}


KNOWN_LOCATION_WORDS = {
    "chegutu", "kadoma", "norton", "harare", "kwekwe", "gweru",
    "chinhoyi", "bindura", "ruwa", "chitungwiza", "marondera",
    "bulawayo", "rimuka", "epworth",
}


def clean_text(value: str) -> str:
    if not value:
        return ""

    return str(value).strip().lower()


def tokenize(text: str):
    text = clean_text(text)
    text = re.sub(r"[^a-zA-Z0-9\.\s]", " ", text)
    return [word for word in text.split() if word]


def get_alias_map():
    response = supabase.table("commodity_aliases").select("*").execute()
    rows = response.data or []

    alias_map = {}

    for row in rows:
        alias = clean_text(row.get("alias"))
        normalized = clean_text(row.get("normalized"))

        if alias and normalized:
            alias_map[alias] = normalized

    alias_map.update(COMMON_COMMODITIES)

    return alias_map


def normalize_unit(value: str):
    value = clean_text(value)

    if not value:
        return None

    if value in UNIT_ALIASES:
        return UNIT_ALIASES[value]

    close = get_close_matches(value, UNIT_ALIASES.keys(), n=1, cutoff=0.84)

    if close:
        return UNIT_ALIASES[close[0]]

    return None


def normalize_number(token: str):
    token = clean_text(token)

    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "dozen": 12,
        "half": 0.5,
    }

    if token in number_words:
        return number_words[token]

    try:
        if "." in token:
            return float(token)

        return int(token)
    except ValueError:
        return None


def extract_quantity_and_unit(text: str):
    tokens = tokenize(text)

    for index, token in enumerate(tokens):
        quantity = normalize_number(token)

        if quantity is None:
            continue

        unit = None

        if index + 1 < len(tokens):
            unit = normalize_unit(tokens[index + 1])

        if token == "half" and index + 1 < len(tokens):
            unit = normalize_unit(tokens[index + 1])

        raw_quantity_text = str(quantity)

        if unit:
            raw_quantity_text = f"{quantity} {unit}"

        return quantity, unit, raw_quantity_text

    return None, None, None


def normalize_commodity(value: str):
    if not value:
        return None

    value = clean_text(value)
    alias_map = get_alias_map()

    if value in alias_map:
        return alias_map[value]

    # Phrase match first
    for alias, normalized in alias_map.items():
        if " " in alias and alias in value:
            return normalized

    close = get_close_matches(value, alias_map.keys(), n=1, cutoff=0.82)

    if close:
        return alias_map[close[0]]

    return value


def guess_commodity_from_text(text: str, reporter_phone: str | None = None):
    tokens = tokenize(text)
    alias_map = get_alias_map()
    clean_message = clean_text(text)

    # Multi-word aliases first
    for alias, normalized in alias_map.items():
        if " " in alias and alias in clean_message:
            return normalized

    # Exact token aliases
    for token in tokens:
        if token in alias_map:
            return alias_map[token]

    # Fuzzy token aliases
    for token in tokens:
        close = get_close_matches(token, alias_map.keys(), n=1, cutoff=0.82)

        if close:
            return alias_map[close[0]]

    # Unknown term logging
    for token in tokens:
        if should_log_unknown(token):
            log_unknown_term(token, text, reporter_phone)

    return None


def should_log_unknown(token: str):
    token = clean_text(token)

    if not token:
        return False

    if token.isdigit():
        return False

    if normalize_number(token) is not None:
        return False

    if token in STOP_WORDS:
        return False

    if token in KNOWN_LOCATION_WORDS:
        return False

    if normalize_unit(token):
        return False

    return True


def log_unknown_term(term: str, context: str, reporter_phone: str | None = None):
    term = clean_text(term)

    if not should_log_unknown(term):
        return None

    existing = (
        supabase.table("unknown_terms")
        .select("*")
        .eq("term", term)
        .eq("status", "pending")
        .limit(1)
        .execute()
    )

    now = datetime.now(timezone.utc).isoformat()

    if existing.data:
        row = existing.data[0]

        reporter_phones = row.get("reporter_phones") or []

        if reporter_phone and reporter_phone not in reporter_phones:
            reporter_phones.append(reporter_phone)

        unique_reporters = len(reporter_phones)
        new_count = (row.get("count") or 1) + 1

        supabase.table("unknown_terms").update({
            "count": new_count,
            "context": context,
            "reporter_phones": reporter_phones,
            "unique_reporters": unique_reporters,
            "last_seen_at": now,
        }).eq("id", row["id"]).execute()

        if (
            new_count >= AUTO_PROMOTE_COUNT_THRESHOLD
            and unique_reporters >= AUTO_PROMOTE_UNIQUE_USERS_THRESHOLD
        ):
            auto_promote_unknown_term(term)

        return row

    reporter_phones = []

    if reporter_phone:
        reporter_phones.append(reporter_phone)

    response = (
        supabase.table("unknown_terms")
        .insert({
            "term": term,
            "context": context,
            "count": 1,
            "status": "pending",
            "reporter_phones": reporter_phones,
            "unique_reporters": len(reporter_phones),
            "first_seen_at": now,
            "last_seen_at": now,
        })
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def auto_promote_unknown_term(term: str):
    term = clean_text(term)

    if not term:
        return None

    existing_alias = (
        supabase.table("commodity_aliases")
        .select("*")
        .eq("alias", term)
        .limit(1)
        .execute()
    )

    if existing_alias.data:
        return existing_alias.data[0]

    response = (
        supabase.table("commodity_aliases")
        .insert({
            "alias": term,
            "normalized": term,
            "auto_learned": True,
        })
        .execute()
    )

    supabase.table("unknown_terms").update({
        "status": "auto_promoted",
        "auto_promoted": True,
        "suggested_normalized": term,
    }).eq("term", term).execute()

    if response.data:
        return response.data[0]

    return None


def fallback_extract_market_data(text: str, reporter_phone: str | None = None):
    commodity = guess_commodity_from_text(text, reporter_phone)
    quantity, unit, raw_quantity_text = extract_quantity_and_unit(text)

    location = None
    lower_text = clean_text(text)

    for loc in KNOWN_LOCATION_WORDS:
        if loc in lower_text:
            location = loc.title()
            break

    return {
        "commodity": commodity or "unknown",
        "quantity": quantity or 0,
        "unit": unit,
        "raw_quantity_text": raw_quantity_text,
        "location": location or "unknown",
        "intent": "sell",
        "confidence": 0.5,
    }


def apply_normalization(
    extracted: dict,
    raw_text: str = "",
    reporter_phone: str | None = None,
):
    fallback = fallback_extract_market_data(raw_text, reporter_phone)

    commodity = extracted.get("commodity") or fallback.get("commodity")
    quantity = extracted.get("quantity") or fallback.get("quantity")
    unit = extracted.get("unit") or fallback.get("unit")
    raw_quantity_text = (
        extracted.get("raw_quantity_text")
        or fallback.get("raw_quantity_text")
    )
    location = extracted.get("location") or fallback.get("location")

    normalized_commodity = normalize_commodity(commodity)

    extracted["commodity"] = normalized_commodity or commodity or "unknown"
    extracted["quantity"] = quantity or 0
    extracted["unit"] = unit
    extracted["raw_quantity_text"] = raw_quantity_text
    extracted["location"] = location or "unknown"

    return extracted