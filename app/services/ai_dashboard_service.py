from collections import Counter
from datetime import datetime, timezone

from google import genai

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.db.supabase_client import supabase


def get_gemini_client():
    if not GEMINI_API_KEY:
        return None

    return genai.Client(api_key=GEMINI_API_KEY)


def safe_fetch(table_name: str, limit: int = 200):
    try:
        response = (
            supabase.table(table_name)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        print(f"AI dashboard fetch error for {table_name}:", e)
        return []


def build_market_snapshot():
    listings = safe_fetch("listings", 300)
    deals = safe_fetch("deals", 200)
    users = safe_fetch("user_profiles", 200)
    untrusted = safe_fetch("untrusted_queue", 100)
    fraud = safe_fetch("fraud_reports", 100)

    active_listings = [
        item for item in listings
        if item.get("status") == "active"
    ]

    sell_requests = [
        item for item in active_listings
        if item.get("intent") == "sell"
    ]

    buy_requests = [
        item for item in active_listings
        if item.get("intent") == "buy"
    ]

    confirmed_deals = [
        item for item in deals
        if item.get("status") == "confirmed"
    ]

    commodities = Counter(
        item.get("commodity")
        for item in active_listings
        if item.get("commodity")
    )

    locations = Counter(
        item.get("location")
        for item in active_listings
        if item.get("location")
    )

    priced_items = [
        item for item in listings
        if item.get("price_per_unit")
    ]

    avg_price_by_commodity = {}
    grouped_prices = {}

    for item in priced_items:
        commodity = item.get("commodity")
        price_per_unit = item.get("price_per_unit")

        if not commodity or not price_per_unit:
            continue

        try:
            grouped_prices.setdefault(commodity, []).append(float(price_per_unit))
        except Exception:
            continue

    for commodity, prices in grouped_prices.items():
        if prices:
            avg_price_by_commodity[commodity] = round(sum(prices) / len(prices), 2)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_users": len(users),
        "total_listings_checked": len(listings),
        "active_requests": len(active_listings),
        "active_sell_requests": len(sell_requests),
        "active_buy_requests": len(buy_requests),
        "confirmed_deals": len(confirmed_deals),
        "untrusted_items": len(untrusted),
        "fraud_reports": len(fraud),
        "top_commodities": commodities.most_common(10),
        "top_locations": locations.most_common(10),
        "avg_price_by_commodity": avg_price_by_commodity,
    }


def build_fallback_summary(snapshot: dict):
    top_commodities = snapshot.get("top_commodities") or []
    top_locations = snapshot.get("top_locations") or []

    commodity_text = ", ".join(
        [f"{name} ({count})" for name, count in top_commodities[:5]]
    ) or "No active commodity data yet"

    location_text = ", ".join(
        [f"{name} ({count})" for name, count in top_locations[:5]]
    ) or "No active location data yet"

    return (
        f"Marketplace summary:\n\n"
        f"Active requests: {snapshot.get('active_requests', 0)}\n"
        f"Sell requests: {snapshot.get('active_sell_requests', 0)}\n"
        f"Buy requests: {snapshot.get('active_buy_requests', 0)}\n"
        f"Confirmed deals: {snapshot.get('confirmed_deals', 0)}\n"
        f"Untrusted queue items: {snapshot.get('untrusted_items', 0)}\n"
        f"Fraud reports: {snapshot.get('fraud_reports', 0)}\n\n"
        f"Top commodities: {commodity_text}\n"
        f"Top locations: {location_text}\n\n"
        f"Recommended action: review unmatched active requests, check untrusted items, and promote high-demand commodities."
    )


def generate_ai_market_summary():
    snapshot = build_market_snapshot()

    client = get_gemini_client()

    if not client:
        return {
            "snapshot": snapshot,
            "summary": build_fallback_summary(snapshot),
        }

    prompt = f"""
You are the admin intelligence assistant for Agri Broker, a Zimbabwe WhatsApp agricultural marketplace.

Use this marketplace snapshot to write a practical admin summary.

Snapshot:
{snapshot}

Write:
1. Short overall status
2. Top demand/supply signals
3. Price insights if available
4. Risk/trust concerns
5. Recommended actions for the operator

Keep it concise.
Do not invent data that is not in the snapshot.
Do not use markdown tables.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        summary = (response.text or "").strip()

        if not summary:
            summary = build_fallback_summary(snapshot)

        return {
            "snapshot": snapshot,
            "summary": summary,
        }

    except Exception as e:
        print("AI dashboard summary error:", e)

        return {
            "snapshot": snapshot,
            "summary": build_fallback_summary(snapshot),
        }