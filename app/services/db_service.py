from datetime import datetime, timezone

from app.db.supabase_client import supabase


def save_listing(data):
    response = supabase.table("listings").insert({
        "type": data.get("type", "listing"),
        "commodity": data.get("commodity"),
        "quantity": data.get("quantity"),
        "unit": data.get("unit"),
        "raw_quantity_text": data.get("raw_quantity_text"),
        "location": data.get("location"),
        "intent": data.get("intent"),
        "confidence": data.get("confidence"),
        "raw_message": data.get("raw", ""),
        "seller_phone": data.get("seller_phone"),
        "status": "active",

        # Price intelligence
        "price": data.get("price"),
        "currency": data.get("currency") or "USD",
        "price_per_unit": data.get("price_per_unit"),

        # Transport intelligence
        "transport_needed": data.get("transport_needed") or False,
        "delivery_option": data.get("delivery_option"),
        "transport_note": data.get("transport_note"),

        # Radius/location intelligence
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "radius_km": data.get("radius_km") or 80,
        "location_source": data.get("location_source"),
    }).execute()

    if response.data:
        return response.data[0]

    return None


def get_listing_by_id(listing_id):
    response = (
        supabase.table("listings")
        .select("*")
        .eq("id", listing_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def get_active_opposite_listings(intent: str, exclude_phone: str | None = None):
    opposite_intent = "buy" if intent == "sell" else "sell"

    query = (
        supabase.table("listings")
        .select("*")
        .eq("status", "active")
        .eq("intent", opposite_intent)
        .order("created_at", desc=True)
    )

    if exclude_phone:
        query = query.neq("seller_phone", exclude_phone)

    response = query.execute()

    return response.data or []


def get_active_listings_by_phone(phone: str, limit: int = 5):
    response = (
        supabase.table("listings")
        .select("*")
        .eq("seller_phone", phone)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data or []


def get_recent_price_comparables(
    commodity: str,
    location: str | None = None,
    limit: int = 50,
):
    if not commodity:
        return []

    query = (
        supabase.table("listings")
        .select("id, commodity, location, intent, price, currency, price_per_unit, unit, created_at, status")
        .eq("commodity", commodity)
        .eq("intent", "sell")
        .not_.is_("price_per_unit", "null")
        .order("created_at", desc=True)
        .limit(limit)
    )

    response = query.execute()
    rows = response.data or []

    if location:
        location_lower = str(location).lower()
        same_location = [
            row for row in rows
            if location_lower in str(row.get("location") or "").lower()
            or str(row.get("location") or "").lower() in location_lower
        ]

        if len(same_location) >= 3:
            return same_location

    return rows


def mark_listing_matched(listing_id):
    response = (
        supabase.table("listings")
        .update({
            "status": "matched",
            "matched_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", listing_id)
        .execute()
    )

    return response.data


def close_listing(listing_id, phone: str, status: str):
    allowed_statuses = ["cancelled", "fulfilled", "closed", "expired"]

    if status not in allowed_statuses:
        return None

    response = (
        supabase.table("listings")
        .update({
            "status": status,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", listing_id)
        .eq("seller_phone", phone)
        .execute()
    )

    return response.data or []