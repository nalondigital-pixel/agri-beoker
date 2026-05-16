from datetime import datetime, timezone

from app.db.supabase_client import supabase


def create_deal(listing_id, buyer, seller_phone=None):
    deal_data = {
        "listing_id": listing_id,
        "buyer_id": buyer.get("id"),
        "buyer_phone": buyer.get("phone"),
        "seller_phone": seller_phone,
        "status": "buyer_alerted",
        "buyer_decision": "pending",
        "seller_decision": "pending",
    }

    response = supabase.table("deals").insert(deal_data).execute()

    if response.data:
        return response.data[0]

    return None


def find_pending_deal_by_buyer_phone(phone):
    response = (
        supabase.table("deals")
        .select("*")
        .eq("buyer_phone", phone)
        .in_("status", ["buyer_alerted", "buyer_interested"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def find_pending_seller_decision(phone):
    response = (
        supabase.table("deals")
        .select("*")
        .eq("seller_phone", phone)
        .eq("status", "buyer_interested")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def update_deal_status(deal_id, status):
    payload = {"status": status}

    if status == "confirmed":
        payload["confirmed_at"] = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("deals")
        .update(payload)
        .eq("id", deal_id)
        .execute()
    )

    return response.data


def update_buyer_decision(deal_id, decision):
    response = (
        supabase.table("deals")
        .update({"buyer_decision": decision})
        .eq("id", deal_id)
        .execute()
    )

    return response.data


def update_seller_decision(deal_id, decision):
    response = (
        supabase.table("deals")
        .update({"seller_decision": decision})
        .eq("id", deal_id)
        .execute()
    )

    return response.data