from app.db.supabase_client import supabase
from app.services.geo_service import get_location_match_info


def normalize_text(value):
    if not value:
        return ""

    return str(value).strip().lower()


def singularize(value):
    value = normalize_text(value)

    if value.endswith("ies"):
        return value[:-3] + "y"

    if value.endswith("es") and len(value) > 3:
        return value[:-2]

    if value.endswith("s") and len(value) > 3:
        return value[:-1]

    return value


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

    singular_a = singularize(item_a)
    singular_b = singularize(item_b)

    return (
        item_a == item_b
        or singular_a == singular_b
        or item_a in item_b
        or item_b in item_a
        or singular_a in singular_b
        or singular_b in singular_a
    )


def unit_score(unit_a, unit_b):
    unit_a = normalize_text(unit_a)
    unit_b = normalize_text(unit_b)

    if not unit_a or not unit_b:
        return 5, "Unit flexible"

    if unit_a == unit_b:
        return 10, "Same unit"

    return 3, "Different unit but still possible"


def buyer_table_quantity_score(seller_quantity, buyer_quantity):
    seller_quantity = normalize_number(seller_quantity)
    buyer_quantity = normalize_number(buyer_quantity)

    if not seller_quantity or not buyer_quantity:
        return 5, "Quantity flexible"

    if seller_quantity >= buyer_quantity:
        return 15, "Seller quantity can satisfy buyer"

    if seller_quantity >= buyer_quantity * 0.5:
        return 8, "Seller has partial quantity"

    return 2, "Quantity may still be negotiable"


def listing_quantity_score(sell_listing, buy_listing):
    sell_quantity = normalize_number(sell_listing.get("quantity"))
    buy_quantity = normalize_number(buy_listing.get("quantity"))

    if not sell_quantity or not buy_quantity:
        return 5, "Quantity flexible"

    if sell_quantity == buy_quantity:
        return 15, "Exact quantity match"

    if sell_quantity >= buy_quantity:
        return 15, "Seller has enough quantity"

    if sell_quantity >= buy_quantity * 0.5:
        return 8, "Seller has partial quantity"

    return 2, "Quantity may still be negotiable"


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

    q_score, q_reason = buyer_table_quantity_score(
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
    reasons = []
    score = 0

    new_intent = normalize_text(new_listing.get("intent"))
    existing_intent = normalize_text(existing_listing.get("intent"))

    if not new_intent or not existing_intent:
        return 0, ["Missing intent"], None

    if new_intent == existing_intent:
        return 0, ["Same intent"], None

    if new_listing.get("seller_phone") == existing_listing.get("seller_phone"):
        return 0, ["Same user ignored"], None

    if not commodity_matches(
        new_listing.get("commodity"),
        existing_listing.get("commodity"),
    ):
        return 0, [
            f"Commodity does not match: {new_listing.get('commodity')} vs {existing_listing.get('commodity')}"
        ], None

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

    if new_intent == "sell":
        sell_listing = new_listing
        buy_listing = existing_listing
    else:
        sell_listing = existing_listing
        buy_listing = new_listing

    q_score, q_reason = listing_quantity_score(sell_listing, buy_listing)
    score += q_score
    reasons.append(q_reason)

    u_score, u_reason = unit_score(
        sell_listing.get("unit"),
        buy_listing.get("unit"),
    )
    score += u_score
    reasons.append(u_reason)

    return score, reasons, geo_info


def find_active_listing_matches(new_listing, active_opposite_listings):
    matches = []

    print("\n========== ACTIVE MATCH DEBUG ==========")
    print("NEW LISTING:", new_listing)
    print("ACTIVE OPPOSITES FOUND:", len(active_opposite_listings))

    for existing_listing in active_opposite_listings:
        score, reasons, geo_info = calculate_listing_to_listing_score(
            new_listing,
            existing_listing,
        )

        print("CHECKING EXISTING:", existing_listing)
        print("SCORE:", score)
        print("REASONS:", reasons)

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

    print("FINAL ACTIVE MATCHES:", len(matches))
    print("========================================\n")

    return matches