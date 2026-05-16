import re
from difflib import get_close_matches

from app.db.supabase_client import supabase


COMMON_COMMODITIES = {
    "tomato": "tomato",
    "tomatoes": "tomato",
    "matomatisi": "tomato",

    "onion": "onion",
    "onions": "onion",

    "potato": "potato",
    "potatoes": "potato",

    "maize": "maize",
    "corn": "maize",
    "chibage": "maize",

    "beans": "beans",
    "bean": "beans",
    "nyemba": "beans",

    "beef": "beef",
    "nyama": "beef",

    "cattle": "cattle",
    "cow": "cattle",
    "cows": "cattle",
    "mombe": "cattle",

    "goat": "goat",
    "goats": "goat",
    "mbudzi": "goat",

    "chicken": "chicken",
    "chickens": "chicken",
    "huku": "chicken",
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
    "bucketful": "buckets",

    "crate": "crates",
    "crates": "crates",

    "box": "boxes",
    "boxes": "boxes",

    "ton": "tons",
    "tons": "tons",
    "tonne": "tons",
    "tonnes": "tons",

    "head": "head",
    "heads": "head",
}


STOP_WORDS = {
    "ndine", "ndiri", "ku", "mu", "pa", "pane", "i", "have",
    "selling", "sell", "available", "in", "at", "the", "a",
    "an", "with", "and", "for", "to", "of", "dziri", "dzinotengeswa",
    "bags", "bag", "kgs", "kg", "bucket", "buckets", "crate", "crates",
    "box", "boxes", "ton", "tons", "tonne", "tonnes",
}


AUTO_PROMOTE_THRESHOLD = 5


def clean_text(value: str) -> str:
    if not value:
        return ""

    return str(value).strip().lower()


def tokenize(text: str):
    text = clean_text(text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
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

    return value


def extract_quantity_and_unit(text: str):
    tokens = tokenize(text)

    for index, token in enumerate(tokens):
        if token.isdigit():
            quantity = int(token)
            unit = None

            if index + 1 < len(tokens):
                possible_unit = normalize_unit(tokens[index + 1])

                if possible_unit:
                    unit = possible_unit

            raw_quantity_text = token

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

    close = get_close_matches(value, alias_map.keys(), n=1, cutoff=0.82)

    if close:
        return alias_map[close[0]]

    return value


def guess_commodity_from_text(text: str):
    tokens = tokenize(text)
    alias_map = get_alias_map()

    for token in tokens:
        if token in alias_map:
            return alias_map[token]

    for token in tokens:
        close = get_close_matches(token, alias_map.keys(), n=1, cutoff=0.82)

        if close:
            return alias_map[close[0]]

    for token in tokens:
        if token not in STOP_WORDS and not token.isdigit():
            log_unknown_term(token, text)

    return None


def log_unknown_term(term: str, context: str):
    term = clean_text(term)

    if not term or term in STOP_WORDS or term.isdigit():
        return None

    existing = (
        supabase.table("unknown_terms")
        .select("*")
        .eq("term", term)
        .eq("status", "pending")
        .limit(1)
        .execute()
    )

    if existing.data:
        row = existing.data[0]
        new_count = (row.get("count") or 1) + 1

        supabase.table("unknown_terms").update({
            "count": new_count,
            "context": context,
        }).eq("id", row["id"]).execute()

        if new_count >= AUTO_PROMOTE_THRESHOLD:
            auto_promote_unknown_term(term)

        return row

    response = (
        supabase.table("unknown_terms")
        .insert({
            "term": term,
            "context": context,
            "count": 1,
            "status": "pending",
        })
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def auto_promote_unknown_term(term: str):
    """
    Safe-ish auto learning:
    If a term appears many times, we add it as its own commodity.
    Example: 'beef' appears often -> beef becomes known.
    Admin can later edit normalized value if needed.
    """

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


def fallback_extract_market_data(text: str):
    commodity = guess_commodity_from_text(text)
    quantity, unit, raw_quantity_text = extract_quantity_and_unit(text)

    known_locations = [
        "chegutu", "kadoma", "norton", "harare",
        "kwekwe", "gweru", "chinhoyi", "bindura",
        "ruwa", "chitungwiza", "marondera", "bulawayo",
    ]

    location = None
    lower_text = clean_text(text)

    for loc in known_locations:
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


def apply_normalization(extracted: dict, raw_text: str = ""):
    fallback = fallback_extract_market_data(raw_text)

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