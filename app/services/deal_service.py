from app.db.supabase_client import supabase


def create_deal(listing_id, buyer):
    deal_data = {
        "listing_id": listing_id,
        "buyer_id": buyer.get("id"),
        "buyer_phone": buyer.get("phone"),
        "status": "pending",
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
        .eq("status", "pending")
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def update_deal_status(deal_id, status):
    response = (
        supabase.table("deals")
        .update({"status": status})
        .eq("id", deal_id)
        .execute()
    )

    return response.data