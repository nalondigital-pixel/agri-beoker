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


def mark_listing_matched(listing_id):
    response = (
        supabase.table("listings")
        .update({
            "status": "matched",
        })
        .eq("id", listing_id)
        .execute()
    )

    return response.data