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


def commodity_matches(item_a, item_b):
    item_a = normalize_text(item_a)
    item_b = normalize_text(item_b)

    if not item_a or not item_b:
        return False

    return (
        item_a == item_b
        or item_a in item_b
        or item_b in item_a
    )


def unit_score(unit_a, unit_b):
    unit_a = normalize_text(unit_a)
    unit_b = normalize_text(unit_b)

    if not unit_a or not unit_b:
        return 5, "Unit flexible"

    if unit_a == unit_b:
        return 10, "Same unit"

    return 0, "Different unit"


def quantity_score(new_quantity, existing_quantity):
    new_quantity = normalize_number(new_quantity)
    existing_quantity = normalize_number(existing_quantity)

    if not new_quantity or not existing_quantity:
        return 5, "Quantity flexible"

    if existing_quantity >= new_quantity:
        return 15, "Quantity compatible"

    if existing_quantity >= new_quantity * 0.5:
        return 8, "Partial quantity compatible"

    return 0, "Quantity too low"


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


def trust_score_from_buyer(buyer):
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
    """
    Existing buyer table matching.
    Used for old buyer records.
    """
    reasons = []
    score = 0

    if not commodity_matches(listing.get("commodity"), buyer.get("commodity")):
        return 0, ["Commodity does not match"], None

    score += 50
    reasons.append("Commodity match")

    geo_info = get_location_match_info(
        listing.get("location"),
        buyer.get("location"),
    )

    if not geo_info.get("compatible"):
        return 0, ["Location too far"], geo_info

    score += geo_score(geo_info)
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

    t_score, t_reasons = trust_score_from_buyer(buyer)
    score += t_score
    reasons.extend(t_reasons)

    return score, reasons, geo_info


def find_matches(listing):
    """
    Matches a new sell request against old buyers table.
    Keeps your existing buyer-table logic working.
    """
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


def calculate_listing_to_listing_score(new_listing, existing_listing):
    """
    Matches active buy/sell listings against each other.
    Example:
    new sell request ↔ old buy request
    new buy request ↔ old sell request
    """
    reasons = []
    score = 0

    if new_listing.get("intent") == existing_listing.get("intent"):
        return 0, ["Same intent"], None

    if not commodity_matches(
        new_listing.get("commodity"),
        existing_listing.get("commodity"),
    ):
        return 0, ["Commodity does not match"], None

    score += 50
    reasons.append("Commodity match")

    geo_info = get_location_match_info(
        new_listing.get("location"),
        existing_listing.get("location"),
    )

    if not geo_info.get("compatible"):
        return 0, ["Location too far"], geo_info

    score += geo_score(geo_info)
    reasons.append(geo_info.get("message", "Location match"))

    q_score, q_reason = quantity_score(
        new_listing.get("quantity"),
        existing_listing.get("quantity"),
    )
    score += q_score
    reasons.append(q_reason)

    u_score, u_reason = unit_score(
        new_listing.get("unit"),
        existing_listing.get("unit"),
    )
    score += u_score
    reasons.append(u_reason)

    return score, reasons, geo_info


def find_active_listing_matches(new_listing, active_opposite_listings):
    matches = []

    for existing_listing in active_opposite_listings:
        score, reasons, geo_info = calculate_listing_to_listing_score(
            new_listing,
            existing_listing,
        )

        if score <= 0:
            continue

        existing_listing["_match_score"] = score
        existing_listing["_match_reasons"] = reasons
        existing_listing["_geo_match_type"] = geo_info.get("match_type") if geo_info else None
        existing_listing["_geo_message"] = geo_info.get("message") if geo_info else "Location match"

        matches.append(existing_listing)

    matches.sort(
        key=lambda item: item.get("_match_score") or 0,
        reverse=True,
    )

    return matches