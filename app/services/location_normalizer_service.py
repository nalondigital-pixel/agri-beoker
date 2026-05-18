import re
from difflib import get_close_matches


ZIMBABWE_LOCATIONS = {
    # Major cities
    "harare": "Harare",
    "hre": "Harare",
    "hararre": "Harare",
    "harar": "Harare",

    "bulawayo": "Bulawayo",
    "bulwayo": "Bulawayo",
    "byo": "Bulawayo",

    "gweru": "Gweru",
    "gwer": "Gweru",

    "mutare": "Mutare",
    "mutar": "Mutare",

    "masvingo": "Masvingo",
    "masving": "Masvingo",

    "kwekwe": "Kwekwe",
    "kwkwe": "Kwekwe",
    "kwe kwe": "Kwekwe",

    "kadoma": "Kadoma",
    "kadma": "Kadoma",
    "kadom": "Kadoma",

    "chinhoyi": "Chinhoyi",
    "chinhoyi town": "Chinhoyi",
    "chinoyi": "Chinhoyi",

    "bindura": "Bindura",
    "marondera": "Marondera",

    # Mashonaland West
    "chegutu": "Chegutu",
    "chegut": "Chegutu",
    "chegu": "Chegutu",
    "chegto": "Chegutu",
    "chegutuu": "Chegutu",

    "norton": "Norton",
    "karoi": "Karoi",
    "kariba": "Kariba",
    "hurungwe": "Hurungwe",
    "magunje": "Magunje",
    "banket": "Banket",
    "zvimba": "Zvimba",
    "raffingora": "Raffingora",
    "selous": "Selous",
    "sanyati": "Sanyati",
    "chakari": "Chakari",

    # Mashonaland East
    "ruwa": "Ruwa",
    "murehwa": "Murehwa",
    "murewa": "Murehwa",
    "mutoko": "Mutoko",
    "uzumba": "Uzumba",
    "wedza": "Wedza",
    "widza": "Wedza",
    "macheke": "Macheke",
    "nyamapanda": "Nyamapanda",
    "mahweshwa": "Mahweshwa",
    "chikomba": "Chikomba",
    "seke": "Seke",

    # Mashonaland Central
    "shamva": "Shamva",
    "mazowe": "Mazowe",
    "mt darwin": "Mount Darwin",
    "mount darwin": "Mount Darwin",
    "darwin": "Mount Darwin",
    "guruve": "Guruve",
    "centenary": "Centenary",
    "muzarabani": "Muzarabani",
    "mbire": "Mbire",
    "rushinga": "Rushinga",

    # Midlands
    "shurugwi": "Shurugwi",
    "mvuma": "Mvuma",
    "gokwe": "Gokwe",
    "gokwe north": "Gokwe North",
    "gokwe south": "Gokwe South",
    "redcliff": "Redcliff",
    "mberengwa": "Mberengwa",
    "zvishavane": "Zvishavane",
    "zvish": "Zvishavane",
    "chirumanzu": "Chirumanzu",
    "lalapanzi": "Lalapanzi",
    "silobela": "Silobela",

    # Manicaland
    "chipinge": "Chipinge",
    "chimanimani": "Chimanimani",
    "nyanga": "Nyanga",
    "rusape": "Rusape",
    "makoni": "Makoni",
    "buhera": "Buhera",
    "birchenough": "Birchenough Bridge",
    "birchenough bridge": "Birchenough Bridge",
    "hauna": "Hauna",
    "murambinda": "Murambinda",

    # Masvingo Province
    "chiredzi": "Chiredzi",
    "triangle": "Triangle",
    "rutenga": "Rutenga",
    "mwenezi": "Mwenezi",
    "zaka": "Zaka",
    "gutu": "Gutu",
    "bikita": "Bikita",
    "chivi": "Chivi",
    "jerera": "Jerera",

    # Matabeleland North
    "hwange": "Hwange",
    "victoria falls": "Victoria Falls",
    "vic falls": "Victoria Falls",
    "binga": "Binga",
    "lupane": "Lupane",
    "nkayi": "Nkayi",
    "tsholotsho": "Tsholotsho",
    "bubi": "Bubi",
    "kamativi": "Kamativi",

    # Matabeleland South
    "gwanda": "Gwanda",
    "beitbridge": "Beitbridge",
    "beit bridge": "Beitbridge",
    "plumtree": "Plumtree",
    "matobo": "Matobo",
    "kezi": "Kezi",
    "filabusi": "Filabusi",
    "insiza": "Insiza",
    "mangwe": "Mangwe",

    # Harare / nearby
    "chitungwiza": "Chitungwiza",
    "chitungiza": "Chitungwiza",
    "chitown": "Chitungwiza",
    "epworth": "Epworth",
    "mabvuku": "Mabvuku",
    "tafara": "Tafara",
    "mufakose": "Mufakose",
    "dzivarasekwa": "Dzivarasekwa",
    "dzivaresekwa": "Dzivarasekwa",
    "glen view": "Glen View",
    "glen norah": "Glen Norah",
    "budiriro": "Budiriro",
    "kuwadzana": "Kuwadzana",
    "mbare": "Mbare",
    "highfield": "Highfield",
    "waterfalls": "Waterfalls",
    "hatfield": "Hatfield",
    "avondale": "Avondale",
    "borrowdale": "Borrowdale",
    "mount pleasant": "Mount Pleasant",
    "mt pleasant": "Mount Pleasant",

    # Bulawayo suburbs / areas
    "luveve": "Luveve",
    "nkulumane": "Nkulumane",
    "emganwini": "Emganwini",
    "makokoba": "Makokoba",
    "pumula": "Pumula",
    "cowdray park": "Cowdray Park",
    "entumbane": "Entumbane",
    "mabutweni": "Mabutweni",

    # Common local areas
    "rimuka": "Rimuka",
    "waverley": "Waverley",
    "eiffel flats": "Eiffel Flats",
    "morningside": "Morningside",
    "mbizo": "Mbizo",
    "amaveni": "Amaveni",
    "senga": "Senga",
    "mkoba": "Mkoba",
    "ascot": "Ascot",
}


LOCATION_NOISE_WORDS = {
    "in",
    "at",
    "ku",
    "kwa",
    "pa",
    "mu",
    "e",
    "near",
    "around",
    "from",
    "to",
    "town",
    "area",
    "farm",
    "growth",
    "point",
    "shopping",
    "centre",
    "center",
    "shops",
    "market",
    "zimbabwe",
    "zim",
    "for",
    "need",
    "want",
    "buy",
    "sell",
    "selling",
    "looking",
    "kg",
    "kgs",
    "bag",
    "bags",
    "box",
    "boxes",
    "crate",
    "crates",
    "beef",
    "maize",
    "tomato",
    "tomatoes",
    "potato",
    "potatoes",
    "goat",
    "goats",
    "cattle",
    "chicken",
    "chickens",
}


def clean_location_text(location: str):
    if not location:
        return ""

    text = str(location).lower().strip()

    text = text.replace(",", " ")
    text = text.replace(".", " ")
    text = text.replace("-", " ")

    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    words = [
        word for word in text.split()
        if word not in LOCATION_NOISE_WORDS
    ]

    return " ".join(words).strip()


def normalize_location_name(location: str):
    """
    Normalize a location field only.
    Use extract_location_from_message() when scanning a full WhatsApp sentence.
    """

    if not location:
        return ""

    cleaned = clean_location_text(location)

    if not cleaned:
        return ""

    if cleaned in ZIMBABWE_LOCATIONS:
        return ZIMBABWE_LOCATIONS[cleaned]

    words = cleaned.split()
    matched_parts = []

    # Exact word/phrase aliases first.
    for alias, official in ZIMBABWE_LOCATIONS.items():
        alias_words = alias.split()

        if len(alias_words) > 1:
            if alias in cleaned and official not in matched_parts:
                matched_parts.append(official)
        else:
            if alias in words and official not in matched_parts:
                matched_parts.append(official)

    # Fuzzy full phrase.
    aliases = list(ZIMBABWE_LOCATIONS.keys())

    full_matches = get_close_matches(
        cleaned,
        aliases,
        n=1,
        cutoff=0.74,
    )

    if full_matches:
        official = ZIMBABWE_LOCATIONS[full_matches[0]]

        if official not in matched_parts:
            matched_parts.append(official)

    # Fuzzy word by word.
    for word in words:
        if len(word) < 4:
            continue

        matches = get_close_matches(
            word,
            aliases,
            n=1,
            cutoff=0.72,
        )

        if matches:
            official = ZIMBABWE_LOCATIONS[matches[0]]

            if official not in matched_parts:
                matched_parts.append(official)

    if matched_parts:
        return ", ".join(matched_parts[:3])

    return str(location).strip().title()


def extract_location_from_message(message: str):
    """
    Scans the whole WhatsApp message for Zimbabwe town/location typos.
    This fixes cases where Gemini/fallback leaves location empty.
    """

    if not message:
        return ""

    cleaned = clean_location_text(message)

    if not cleaned:
        return ""

    words = cleaned.split()
    matched_parts = []

    # 1. Direct alias match by word/phrase.
    for alias, official in ZIMBABWE_LOCATIONS.items():
        alias_words = alias.split()

        if len(alias_words) > 1:
            if alias in cleaned and official not in matched_parts:
                matched_parts.append(official)
        else:
            if alias in words and official not in matched_parts:
                matched_parts.append(official)

    # 2. Fuzzy word-by-word match.
    aliases = list(ZIMBABWE_LOCATIONS.keys())

    for word in words:
        if len(word) < 4:
            continue

        matches = get_close_matches(
            word,
            aliases,
            n=1,
            cutoff=0.72,
        )

        if matches:
            official = ZIMBABWE_LOCATIONS[matches[0]]

            if official not in matched_parts:
                matched_parts.append(official)

    if matched_parts:
        return ", ".join(matched_parts[:3])

    return ""


def best_location(existing_location: str, full_message: str):
    """
    Prefer a normalized extracted location.
    If missing/weak, scan the whole message.
    """

    normalized_existing = normalize_location_name(existing_location or "")
    message_location = extract_location_from_message(full_message or "")

    if normalized_existing and message_location:
        # If existing location is just a typo/short form and message scan found official town,
        # combine unique parts.
        parts = []

        for value in [normalized_existing, message_location]:
            for piece in str(value).split(","):
                piece = piece.strip()

                if piece and piece not in parts:
                    parts.append(piece)

        return ", ".join(parts[:3])

    if normalized_existing:
        return normalized_existing

    if message_location:
        return message_location

    return ""