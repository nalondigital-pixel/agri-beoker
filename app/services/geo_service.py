from app.data.zimbabwe_geo import ZIMBABWE_GEO


def normalize_location(location: str):
    if not location:
        return ""

    return str(location).strip().lower()


def get_location_info(location: str):
    location_key = normalize_location(location)

    if location_key in ZIMBABWE_GEO:
        return ZIMBABWE_GEO[location_key]

    # Try partial match, e.g. "Rimuka Kadoma" contains "kadoma"
    for key, info in ZIMBABWE_GEO.items():
        if key in location_key or location_key in key:
            return info

    return None


def get_display_location(location: str):
    info = get_location_info(location)

    if info:
        return info.get("display")

    return location


def are_locations_compatible(seller_location: str, buyer_location: str):
    seller_key = normalize_location(seller_location)
    buyer_key = normalize_location(buyer_location)

    if not seller_key or not buyer_key:
        return False

    # Exact or partial match
    if seller_key == buyer_key:
        return True

    if seller_key in buyer_key or buyer_key in seller_key:
        return True

    seller_info = get_location_info(seller_key)
    buyer_info = get_location_info(buyer_key)

    if not seller_info or not buyer_info:
        return False

    seller_display = normalize_location(seller_info.get("display"))
    buyer_display = normalize_location(buyer_info.get("display"))

    # Same normalized display
    if seller_display == buyer_display:
        return True

    # Nearby town match
    seller_nearby = seller_info.get("nearby", [])
    buyer_nearby = buyer_info.get("nearby", [])

    if buyer_display in seller_nearby:
        return True

    if seller_display in buyer_nearby:
        return True

    # Same province match as weaker compatibility
    if seller_info.get("province") == buyer_info.get("province"):
        return True

    return False