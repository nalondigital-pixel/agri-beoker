import re
from difflib import get_close_matches

from app.db.supabase_client import supabase


COMMON_COMMODITIES = {
    "tomato": "tomato",
    "tomatoes": "tomato",
    "onion": "onion",
    "onions": "onion",
    "potato": "potato",
    "potatoes": "potato",
    "maize": "maize",
    "corn": "maize",
    "cattle": "cattle",
    "cow": "cattle",
    "cows": "cattle",
    "goat": "goat",
    "goats": "goat",
    "chicken": "chicken",
    "chickens": "chicken",
}


STOP_WORDS = {
    "ndine", "ndiri", "ku", "mu", "pa", "pane", "i", "have",
    "selling", "sell", "available", "in", "at", "the", "a",
    "an", "with", "and", "for", "to", "of", "dziri", "dzinotengeswa",
}


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


def normalize_commodity(value: str):
    """
    Converts slang/local/typo commodity names into a standard commodity name.
    Example:
    - mombe -> cattle
    - mbudzi -> goat
    - chibage -> maize
    """

    if not value:
        return None

    value = clean_text(value)
    alias_map = get_alias_map()

    if value in alias_map:
        return alias_map[value]

    close = get_close_matches(
        value,
        alias_map.keys(),
        n=1,
        cutoff=0.82
    )

    if close:
        return alias_map[close[0]]

    if value in COMMON_COMMODITIES:
        return COMMON_COMMODITIES[value]

    return value


def extract_quantity_from_text(text: str):
    tokens = tokenize(text)

    for token in tokens:
        if token.isdigit():
            return int(token)

    return None


def guess_commodity_from_text(text: str):
    tokens = tokenize(text)
    alias_map = get_alias_map()

    for token in tokens:
        if token in alias_map:
            return alias_map[token]

    for token in tokens:
        close = get_close_matches(
            token,
            alias_map.keys(),
            n=1,
            cutoff=0.82
        )

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


def fallback_extract_market_data(text: str):
    """
    Cheap fallback extractor when AI is down/rate-limited.
    """

    commodity = guess_commodity_from_text(text)
    quantity = extract_quantity_from_text(text)

    # Simple location detection for your pilot areas
    known_locations = [
        "chegutu", "kadoma", "norton", "harare",
        "kwekwe", "gweru", "chinhoyi", "bindura",
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
        "location": location or "unknown",
        "intent": "sell",
        "confidence": 0.5,
    }


def apply_normalization(extracted: dict, raw_text: str = ""):
    """
    Normalizes AI output and fills missing fields using fallback logic.
    """

    fallback = fallback_extract_market_data(raw_text)

    commodity = extracted.get("commodity") or fallback.get("commodity")
    quantity = extracted.get("quantity") or fallback.get("quantity")
    location = extracted.get("location") or fallback.get("location")

    normalized_commodity = normalize_commodity(commodity)

    extracted["commodity"] = normalized_commodity or commodity or "unknown"
    extracted["quantity"] = quantity or 0
    extracted["location"] = location or "unknown"

    return extracted