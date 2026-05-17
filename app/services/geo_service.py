import math

from app.data.zimbabwe_geo import ZIMBABWE_GEO


def normalize_location(location: str):
    if not location:
        return ""

    return str(location).strip().lower()


def get_location_info(location: str):
    location_key = normalize_location(location)

    if location_key in ZIMBABWE_GEO:
        return ZIMBABWE_GEO[location_key]

    for key, info in ZIMBABWE_GEO.items():
        if key in location_key or location_key in key:
            return info

    return None


def get_display_location(location: str):
    info = get_location_info(location)

    if info:
        return info.get("display")

    return location


def calculate_distance_km(location_a: str, location_b: str):
    info_a = get_location_info(location_a)
    info_b = get_location_info(location_b)

    if not info_a or not info_b:
        return None

    lat1 = math.radians(info_a["lat"])
    lon1 = math.radians(info_a["lng"])
    lat2 = math.radians(info_b["lat"])
    lon2 = math.radians(info_b["lng"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(6371 * c)


def get_location_match_info(seller_location: str, buyer_location: str):
    seller_key = normalize_location(seller_location)
    buyer_key = normalize_location(buyer_location)

    if not seller_key or not buyer_key:
        return {
            "compatible": False,
            "match_type": "unknown",
            "distance_km": None,
            "message": "Location unknown",
        }

    distance_km = calculate_distance_km(seller_key, buyer_key)

    if seller_key == buyer_key or seller_key in buyer_key or buyer_key in seller_key:
        return {
            "compatible": True,
            "match_type": "same_location",
            "distance_km": 0,
            "message": "Same location",
        }

    seller_info = get_location_info(seller_key)
    buyer_info = get_location_info(buyer_key)

    if not seller_info or not buyer_info:
        return {
            "compatible": False,
            "match_type": "unknown",
            "distance_km": None,
            "message": "Location not recognized",
        }

    seller_display = normalize_location(seller_info.get("display"))
    buyer_display = normalize_location(buyer_info.get("display"))

    seller_nearby = seller_info.get("nearby", [])
    buyer_nearby = buyer_info.get("nearby", [])

    if buyer_display in seller_nearby or seller_display in buyer_nearby:
        return {
            "compatible": True,
            "match_type": "nearby",
            "distance_km": distance_km,
            "message": f"Nearby area, about {distance_km} km away",
        }

    if distance_km is not None and distance_km <= 80:
        return {
            "compatible": True,
            "match_type": "within_80km",
            "distance_km": distance_km,
            "message": f"Within trading range, about {distance_km} km away",
        }

    if seller_info.get("province") == buyer_info.get("province"):
        return {
            "compatible": True,
            "match_type": "same_province",
            "distance_km": distance_km,
            "message": f"Same province, about {distance_km} km away",
        }

    return {
        "compatible": False,
        "match_type": "far",
        "distance_km": distance_km,
        "message": f"Far location, about {distance_km} km away",
    }


def are_locations_compatible(seller_location: str, buyer_location: str):
    return get_location_match_info(seller_location, buyer_location)["compatible"]