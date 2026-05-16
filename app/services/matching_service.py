from app.db.supabase_client import supabase
from app.services.geo_service import get_location_match_info


def normalize_text(value):
    if not value:
        return ""

    return str(value).strip().lower()


def find_matches(listing):
    commodity = normalize_text(listing.get("commodity"))
    seller_location = normalize_text(listing.get("location"))

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

        geo_info = get_location_match_info(
            seller_location,
            buyer_location
        )

        if commodity_match and geo_info["compatible"]:
            buyer["_geo_match_type"] = geo_info["match_type"]
            buyer["_geo_message"] = geo_info["message"]
            matches.append(buyer)

    matches.sort(
        key=lambda buyer: (
            buyer.get("verified") is True,
            buyer.get("reputation") or 0,
            buyer.get("total_deals") or 0,
            buyer.get("_geo_match_type") == "same_location",
            buyer.get("_geo_match_type") == "nearby",
        ),
        reverse=True,
    )

    return matches