from statistics import median

from app.services.db_service import get_recent_price_comparables


def format_money(value):
    if value is None:
        return "N/A"

    try:
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return str(round(number, 2))

    except Exception:
        return str(value)


def get_price_guidance_for_listing(listing: dict):
    commodity = listing.get("commodity")
    location = listing.get("location")
    price_per_unit = listing.get("price_per_unit")
    currency = listing.get("currency") or "USD"
    unit = listing.get("unit") or "unit"

    if not commodity or not price_per_unit:
        return ""

    comparables = get_recent_price_comparables(
        commodity=commodity,
        location=location,
    )

    prices = []

    for row in comparables:
        value = row.get("price_per_unit")

        try:
            value = float(value)

            if value > 0:
                prices.append(value)

        except Exception:
            continue

    if len(prices) < 3:
        return (
            "💡 Price note: I do not have enough recent market data yet "
            "to judge this price confidently."
        )

    market_median = median(prices)
    user_price = float(price_per_unit)

    low_threshold = market_median * 0.8
    high_threshold = market_median * 1.2

    if user_price < low_threshold:
        label = "LOW"
        advice = "This looks below recent market prices. It may attract buyers quickly, but check that you are not underpricing."
    elif user_price > high_threshold:
        label = "HIGH"
        advice = "This looks above recent market prices. You may get fewer buyers unless quality or delivery justifies it."
    else:
        label = "FAIR"
        advice = "This looks close to recent market prices."

    return (
        f"💡 Price guidance: {label}\n"
        f"Your price: {currency} {format_money(user_price)} per {unit}\n"
        f"Recent estimate: around {currency} {format_money(market_median)} per {unit}\n"
        f"{advice}"
    )