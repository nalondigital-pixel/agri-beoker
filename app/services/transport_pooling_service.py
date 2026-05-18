from datetime import date

from app.db.supabase_client import supabase
from app.services.profile_service import get_profile
from app.services.whatsapp_service import send_whatsapp_buttons, send_whatsapp_message
from app.services.location_pin_service import haversine_distance_km


POOL_RADIUS_KM = 25


def normalize_text(value):
    return str(value or "").strip().lower()


def get_profile_destination(phone: str):
    profile = get_profile(phone)

    if not profile:
        return {
            "destination": None,
            "latitude": None,
            "longitude": None,
        }

    city = profile.get("city")
    area = profile.get("area")
    location_address = profile.get("location_address")

    destination_parts = []

    if area:
        destination_parts.append(area)

    if city:
        destination_parts.append(city)

    destination = ", ".join(destination_parts)

    if not destination:
        destination = location_address

    return {
        "destination": destination,
        "latitude": profile.get("latitude"),
        "longitude": profile.get("longitude"),
    }


def destinations_match(route_a: dict, route_b: dict):
    destination_a = normalize_text(route_a.get("destination"))
    destination_b = normalize_text(route_b.get("destination"))

    if destination_a and destination_b:
        if destination_a == destination_b:
            return True

        if destination_a in destination_b or destination_b in destination_a:
            return True

    lat_a = route_a.get("destination_latitude")
    lng_a = route_a.get("destination_longitude")
    lat_b = route_b.get("destination_latitude")
    lng_b = route_b.get("destination_longitude")

    if lat_a is None or lng_a is None or lat_b is None or lng_b is None:
        return False

    distance = haversine_distance_km(lat_a, lng_a, lat_b, lng_b)

    if distance is None:
        return False

    return distance <= POOL_RADIUS_KM


def origins_are_near(route_a: dict, route_b: dict):
    lat_a = route_a.get("origin_latitude")
    lng_a = route_a.get("origin_longitude")
    lat_b = route_b.get("origin_latitude")
    lng_b = route_b.get("origin_longitude")

    if lat_a is not None and lng_a is not None and lat_b is not None and lng_b is not None:
        distance = haversine_distance_km(lat_a, lng_a, lat_b, lng_b)

        if distance is not None:
            return distance <= POOL_RADIUS_KM

    origin_a = normalize_text(route_a.get("origin"))
    origin_b = normalize_text(route_b.get("origin"))

    if not origin_a or not origin_b:
        return False

    if origin_a == origin_b:
        return True

    if origin_a in origin_b or origin_b in origin_a:
        return True

    return False


def create_transport_route_from_deal(deal: dict, listing: dict):
    """
    Creates a route after a deal is confirmed.

    Origin = seller/listing location.
    Destination = buyer profile city/area/location pin.
    """

    if not deal or not listing:
        return None

    deal_id = deal.get("id")
    listing_id = listing.get("id")

    seller_phone = deal.get("seller_phone")
    buyer_phone = deal.get("buyer_phone")

    destination_data = get_profile_destination(buyer_phone)

    origin = listing.get("location")
    destination = destination_data.get("destination")

    if not origin or not destination:
        print("Transport route skipped: missing origin or destination")
        return None

    response = supabase.table("transport_pool_routes").insert({
        "deal_id": deal_id,
        "listing_id": listing_id,

        "owner_phone": seller_phone,
        "other_party_phone": buyer_phone,

        "origin": origin,
        "origin_latitude": listing.get("latitude"),
        "origin_longitude": listing.get("longitude"),

        "destination": destination,
        "destination_latitude": destination_data.get("latitude"),
        "destination_longitude": destination_data.get("longitude"),

        "commodity": listing.get("commodity"),
        "quantity": listing.get("quantity"),
        "unit": listing.get("unit"),

        "target_date": date.today().isoformat(),
        "status": "active",
    }).execute()

    if response.data:
        return response.data[0]

    return None


def find_poolable_routes(new_route: dict):
    if not new_route:
        return []

    response = (
        supabase.table("transport_pool_routes")
        .select("*")
        .eq("status", "active")
        .eq("target_date", new_route.get("target_date"))
        .neq("id", new_route.get("id"))
        .limit(100)
        .execute()
    )

    routes = response.data or []
    poolable = []

    for route in routes:
        if route.get("owner_phone") == new_route.get("owner_phone"):
            continue

        if not destinations_match(new_route, route):
            continue

        if not origins_are_near(new_route, route):
            continue

        poolable.append(route)

    return poolable


def create_pool_suggestion(new_route: dict, poolable_routes: list):
    all_routes = [new_route] + poolable_routes

    route_ids = []
    notified_phones = []
    total_quantity = 0
    unit = new_route.get("unit")

    for route in all_routes:
        if route.get("id"):
            route_ids.append(route.get("id"))

        if route.get("owner_phone") and route.get("owner_phone") not in notified_phones:
            notified_phones.append(route.get("owner_phone"))

        try:
            total_quantity += float(route.get("quantity") or 0)
        except Exception:
            pass

    response = supabase.table("transport_pool_suggestions").insert({
        "route_ids": route_ids,
        "notified_phones": notified_phones,
        "interested_phones": [],

        "origin_area": new_route.get("origin"),
        "destination": new_route.get("destination"),

        "target_date": new_route.get("target_date"),
        "total_quantity": total_quantity,
        "unit": unit,

        "status": "suggested",
    }).execute()

    if response.data:
        return response.data[0]

    return None


def notify_pool_suggestion(suggestion: dict):
    if not suggestion:
        return 0

    phones = suggestion.get("notified_phones") or []

    origin = suggestion.get("origin_area") or "nearby"
    destination = suggestion.get("destination") or "the same destination"
    target_date = suggestion.get("target_date") or "soon"
    total_quantity = suggestion.get("total_quantity") or 0
    unit = suggestion.get("unit") or ""

    sent_count = 0

    for phone in phones:
        if not phone:
            continue

        send_whatsapp_buttons(
            phone,
            (
                "🚚 Transport Pooling Opportunity\n\n"
                f"We noticed nearby loads from {str(origin).title()} heading to "
                f"{str(destination).title()} around {target_date}.\n\n"
                f"Combined load: {total_quantity} {unit}\n\n"
                "Pooling onto one truck may reduce transport costs."
            ),
            [
                {
                    "id": f"pool_interest_{suggestion.get('id')}",
                    "title": "Interested",
                },
                {
                    "id": f"pool_ignore_{suggestion.get('id')}",
                    "title": "Ignore",
                },
            ],
        )

        sent_count += 1

    return sent_count


def check_and_notify_transport_pooling(deal: dict, listing: dict):
    new_route = create_transport_route_from_deal(deal, listing)

    if not new_route:
        return {
            "status": "no_route_created",
        }

    poolable_routes = find_poolable_routes(new_route)

    if not poolable_routes:
        return {
            "status": "route_created_no_pool",
            "route_id": new_route.get("id"),
        }

    suggestion = create_pool_suggestion(new_route, poolable_routes)

    if not suggestion:
        return {
            "status": "pool_found_but_suggestion_failed",
            "route_id": new_route.get("id"),
            "poolable_count": len(poolable_routes),
        }

    sent_count = notify_pool_suggestion(suggestion)

    return {
        "status": "pool_suggestion_sent",
        "route_id": new_route.get("id"),
        "suggestion_id": suggestion.get("id"),
        "poolable_count": len(poolable_routes),
        "messages_sent": sent_count,
    }


def get_pool_suggestion(suggestion_id: str):
    response = (
        supabase.table("transport_pool_suggestions")
        .select("*")
        .eq("id", suggestion_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def handle_pool_interest(phone: str, suggestion_id: str):
    suggestion = get_pool_suggestion(suggestion_id)

    if not suggestion:
        send_whatsapp_message(
            phone,
            "This transport pooling opportunity was not found or has expired.",
        )

        return {
            "handled": True,
            "status": "not_found",
        }

    interested_phones = suggestion.get("interested_phones") or []

    if phone not in interested_phones:
        interested_phones.append(phone)

    new_status = "ready_to_coordinate" if len(interested_phones) >= 2 else "suggested"

    response = (
        supabase.table("transport_pool_suggestions")
        .update({
            "interested_phones": interested_phones,
            "status": new_status,
        })
        .eq("id", suggestion_id)
        .execute()
    )

    send_whatsapp_message(
        phone,
        (
            "✅ Noted. You are interested in pooling transport.\n\n"
            "If enough people confirm, Agri Broker will help coordinate the shared route."
        ),
    )

    if len(interested_phones) >= 2:
        notified_phones = suggestion.get("notified_phones") or []

        for target_phone in notified_phones:
            if not target_phone:
                continue

            send_whatsapp_message(
                target_phone,
                (
                    "🚚 Transport Pooling Update\n\n"
                    "At least 2 people are interested in sharing transport for this route.\n\n"
                    "You can coordinate directly or wait for Agri Broker admin support."
                ),
            )

    return {
        "handled": True,
        "status": "interest_recorded",
        "interested_count": len(interested_phones),
        "data": response.data,
    }


def handle_pool_ignore(phone: str, suggestion_id: str):
    send_whatsapp_message(
        phone,
        "No problem. We will ignore this transport pooling opportunity for now.",
    )

    return {
        "handled": True,
        "status": "ignored",
    }