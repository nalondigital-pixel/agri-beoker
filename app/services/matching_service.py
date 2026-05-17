from app.db.supabase_client import supabase
from app.services.geo_service import get_location_match_info


def normalize_text(value):
    if not value:
        return ""

    return str(value).strip().lower()


def normalize_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def commodity_matches(listing_commodity, buyer_commodity):
    listing_commodity = normalize_text(listing_commodity)
    buyer_commodity = normalize_text(buyer_commodity)

    if not listing_commodity or not buyer_commodity:
        return False

    return (
        listing_commodity == buyer_commodity
        or listing_commodity in buyer_commodity
        or buyer_commodity in listing_commodity
    )


def unit_score(listing_unit, buyer_unit):
    listing_unit = normalize_text(listing_unit)
    buyer_unit = normalize_text(buyer_unit)

    if not listing_unit or not buyer_unit:
        return 5, "Unit flexible"

    if listing_unit == buyer_unit:
        return 10, "Same unit"

    return 0, "Different unit"


def quantity_score(listing_quantity, buyer_quantity):
    listing_quantity = normalize_number(listing_quantity)
    buyer_quantity = normalize_number(buyer_quantity)

    if not listing_quantity or not buyer_quantity:
        return 5, "Quantity flexible"

    if buyer_quantity >= listing_quantity:
        return 15, "Buyer can take full quantity"

    if buyer_quantity >= listing_quantity * 0.5:
        return 8, "Buyer can take partial quantity"

    return 0, "Buyer quantity too low"


def geo_score(geo_info):
    match_type = geo_info.get("match_type")

    if match_type == "same_location":
        return 25

    if match_type == "nearby":
        return 20

    if match_type == "within_80km":
        return 16

    if match_type == "same_province":
        return 10

    return 0


def trust_score(buyer):
    score = 0
    reasons = []

    if buyer.get("verified") is True:
        score += 10
        reasons.append("Verified buyer")

    reputation = buyer.get("reputation") or 0
    total_deals = buyer.get("total_deals") or 0

    if reputation:
        score += min(int(reputation), 10)
        reasons.append(f"Reputation {reputation}")

    if total_deals:
        score += min(int(total_deals), 10)
        reasons.append(f"{total_deals} past deals")

    return score, reasons


def calculate_match_score(listing, buyer):
    reasons = []
    score = 0

    listing_commodity = listing.get("commodity")
    buyer_commodity = buyer.get("commodity")

    if not commodity_matches(listing_commodity, buyer_commodity):
        return 0, ["Commodity does not match"], None

    score += 50
    reasons.append("Commodity match")

    geo_info = get_location_match_info(
        listing.get("location"),
        buyer.get("location"),
    )

    if not geo_info.get("compatible"):
        return 0, ["Location too far"], geo_info

    location_points = geo_score(geo_info)
    score += location_points
    reasons.append(geo_info.get("message", "Location match"))

    q_score, q_reason = quantity_score(
        listing.get("quantity"),
        buyer.get("quantity"),
    )
    score += q_score
    reasons.append(q_reason)

    u_score, u_reason = unit_score(
        listing.get("unit"),
        buyer.get("unit"),
    )
    score += u_score
    reasons.append(u_reason)

    t_score, t_reasons = trust_score(buyer)
    score += t_score
    reasons.extend(t_reasons)

    return score, reasons, geo_info


def find_matches(listing):
    response = supabase.table("buyers").select("*").execute()

    buyers = response.data or []
    matches = []

    for buyer in buyers:
        score, reasons, geo_info = calculate_match_score(listing, buyer)

        if score <= 0:
            continue

        buyer["_match_score"] = score
        buyer["_match_reasons"] = reasons
        buyer["_geo_match_type"] = geo_info.get("match_type") if geo_info else None
        buyer["_geo_message"] = geo_info.get("message") if geo_info else "Location match"

        matches.append(buyer)

    matches.sort(
        key=lambda buyer: buyer.get("_match_score") or 0,
        reverse=True,
    )

    return matches