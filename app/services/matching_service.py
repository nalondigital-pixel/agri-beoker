from app.db.supabase_client import supabase


def normalize_text(value):
    if not value:
        return ""

    return str(value).strip().lower()


def find_matches(listing):
    commodity = normalize_text(listing.get("commodity"))
    location = normalize_text(listing.get("location"))

    response = supabase.table("buyers").select("*").execute()

    buyers = response.data or []
    matches = []

    for buyer in buyers:
        buyer_commodity = normalize_text(buyer.get("commodity"))
        buyer_location = normalize_text(buyer.get("location"))

        commodity_match = (
            commodity in buyer_commodity
            or buyer_commodity in commodity
        )

        location_match = (
            location in buyer_location
            or buyer_location in location
        )

        if commodity_match and location_match:
            matches.append(buyer)

    # Verified buyers first, then highest reputation, then most deals
    matches.sort(
        key=lambda buyer: (
            buyer.get("verified") is True,
            buyer.get("reputation") or 0,
            buyer.get("total_deals") or 0,
        ),
        reverse=True,
    )

    return matches