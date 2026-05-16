from app.db.supabase_client import supabase


# =========================
# MATCHING ENGINE
# =========================
def find_matches(listing):
    commodity = listing.get("commodity", "").strip().lower()
    location = listing.get("location", "").strip().lower()

    # Get all buyers
    response = supabase.table("buyers").select("*").execute()

    buyers = response.data or []
    matches = []

    for b in buyers:
        b_commodity = (b.get("commodity") or "").strip().lower()
        b_location = (b.get("location") or "").strip().lower()

        # FLEXIBLE MATCHING (real-world friendly)
        commodity_match = commodity in b_commodity or b_commodity in commodity
        location_match = location in b_location or b_location in location

        if commodity_match and location_match:
            matches.append(b)

    return matches