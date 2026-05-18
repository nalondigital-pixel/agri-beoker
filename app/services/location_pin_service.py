import math

from app.services.profile_service import get_profile, update_profile
from app.services.geo_service import get_location_info


DEFAULT_RADIUS_KM = 80


def haversine_distance_km(lat1, lng1, lat2, lng2):
    """
    Calculates distance between two GPS points in kilometers.
    This is self-contained so we do not depend on geo_service's function signature.
    """

    try:
        lat1 = float(lat1)
        lng1 = float(lng1)
        lat2 = float(lat2)
        lng2 = float(lng2)
    except Exception:
        return None

    earth_radius_km = 6371

    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_km * c


def extract_location_pin(message_data: dict):
    """
    WhatsApp location messages usually arrive as:
    {
      "location": {
        "latitude": ...,
        "longitude": ...,
        "name": "...",
        "address": "..."
      }
    }
    """

    location = message_data.get("location")

    if not location:
        return None

    latitude = location.get("latitude")
    longitude = location.get("longitude")

    if latitude is None or longitude is None:
        return None

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except Exception:
        return None

    return {
        "latitude": latitude,
        "longitude": longitude,
        "name": location.get("name"),
        "address": location.get("address"),
    }


def save_user_location_pin(phone: str, location_pin: dict):
    if not location_pin:
        return None

    address = (
        location_pin.get("address")
        or location_pin.get("name")
        or "WhatsApp location pin"
    )

    return update_profile(phone, {
        "latitude": location_pin.get("latitude"),
        "longitude": location_pin.get("longitude"),
        "location_address": address,
        "location_source": "whatsapp_pin",
    })


def get_user_coordinates(phone: str):
    profile = get_profile(phone)

    if not profile:
        return None

    latitude = profile.get("latitude")
    longitude = profile.get("longitude")

    if latitude is None or longitude is None:
        return None

    try:
        return {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "address": profile.get("location_address"),
        }
    except Exception:
        return None


def attach_profile_coordinates_to_listing(phone: str, listing: dict):
    """
    If the listing has no lat/lng, use the user's saved WhatsApp pin.
    """

    if listing.get("latitude") is not None and listing.get("longitude") is not None:
        return listing

    coords = get_user_coordinates(phone)

    if not coords:
        return listing

    listing["latitude"] = coords.get("latitude")
    listing["longitude"] = coords.get("longitude")
    listing["location_source"] = "profile_whatsapp_pin"

    if not listing.get("location") and coords.get("address"):
        listing["location"] = coords.get("address")

    return listing


def attach_direct_pin_to_listing(listing: dict, location_pin: dict):
    if not location_pin:
        return listing

    listing["latitude"] = location_pin.get("latitude")
    listing["longitude"] = location_pin.get("longitude")
    listing["location_source"] = "whatsapp_pin"

    address = (
        location_pin.get("address")
        or location_pin.get("name")
        or listing.get("location")
    )

    if address:
        listing["location"] = address

    return listing


def get_coordinates_from_listing(listing: dict):
    if not listing:
        return None

    latitude = listing.get("latitude")
    longitude = listing.get("longitude")

    if latitude is not None and longitude is not None:
        try:
            return {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "source": listing.get("location_source") or "listing_pin",
            }
        except Exception:
            pass

    location_name = listing.get("location")

    if not location_name:
        return None

    info = get_location_info(location_name)

    if not info:
        return None

    return {
        "latitude": info.get("lat"),
        "longitude": info.get("lng"),
        "source": "known_location",
    }


def distance_between_listings(listing_a: dict, listing_b: dict):
    coords_a = get_coordinates_from_listing(listing_a)
    coords_b = get_coordinates_from_listing(listing_b)

    if not coords_a or not coords_b:
        return None

    distance = haversine_distance_km(
        coords_a.get("latitude"),
        coords_a.get("longitude"),
        coords_b.get("latitude"),
        coords_b.get("longitude"),
    )

    if distance is None:
        return None

    return round(distance, 1)


def enrich_and_sort_matches_by_radius(base_listing: dict, matches: list):
    """
    Adds _distance_km and sorts closest first.
    If coordinates are missing, keeps match but places it lower.
    """

    if not matches:
        return []

    try:
        radius_km = float(base_listing.get("radius_km") or DEFAULT_RADIUS_KM)
    except Exception:
        radius_km = DEFAULT_RADIUS_KM

    enriched = []

    for match in matches:
        distance_km = distance_between_listings(base_listing, match)

        match["_distance_km"] = distance_km

        if distance_km is not None:
            match["_geo_message"] = f"About {distance_km} km away"

            if distance_km <= radius_km:
                match["_radius_match"] = True
                match["_radius_message"] = f"Within your {int(radius_km)} km radius"
            else:
                match["_radius_match"] = False
                match["_radius_message"] = f"Outside your {int(radius_km)} km radius"
        else:
            match["_radius_match"] = None
            match["_radius_message"] = "Distance unknown"

        enriched.append(match)

    def sort_key(item):
        distance = item.get("_distance_km")

        if distance is None:
            return (2, 999999)

        if item.get("_radius_match"):
            return (0, distance)

        return (1, distance)

    return sorted(enriched, key=sort_key)


def filter_matches_within_radius(base_listing: dict, matches: list):
    """
    Keep matches inside radius.
    If no coordinates exist, keep them so old town-based matching still works.
    """

    enriched = enrich_and_sort_matches_by_radius(base_listing, matches)

    filtered = []

    for match in enriched:
        distance = match.get("_distance_km")

        if distance is None:
            filtered.append(match)
            continue

        if match.get("_radius_match"):
            filtered.append(match)

    return filtered


def build_location_pin_reply(location_pin: dict):
    address = location_pin.get("address") or location_pin.get("name") or "your pinned location"

    return (
        "✅ Location pin saved.\n\n"
        f"Location: {address}\n\n"
        "I will use this to prioritize nearby buyers and sellers."
    )