from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.config import DASHBOARD_PASSWORD
from app.services.ai_dashboard_service import generate_ai_market_summary

router = APIRouter(prefix="/admin-ai", tags=["Admin AI"])


@router.get("/summary")
def ai_summary(password: str = Query(None)):
    if password != DASHBOARD_PASSWORD:
        return {"status": "unauthorized"}

    result = generate_ai_market_summary()

    return {
        "status": "ok",
        "summary": result.get("summary"),
        "snapshot": result.get("snapshot"),
    }


@router.get("/summary-html", response_class=HTMLResponse)
def ai_summary_html(password: str = Query(None)):
    if password != DASHBOARD_PASSWORD:
        return HTMLResponse("<h1>Unauthorized</h1>", status_code=401)

    result = generate_ai_market_summary()
    summary = result.get("summary") or ""
    snapshot = result.get("snapshot") or {}

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agri Broker AI Summary</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f6f7f9;
                padding: 24px;
                color: #111827;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 24px;
                max-width: 900px;
                margin: 0 auto 20px auto;
                box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            }}
            pre {{
                white-space: pre-wrap;
                font-size: 15px;
                line-height: 1.5;
            }}
            .stat {{
                display: inline-block;
                background: #eef2ff;
                padding: 10px 14px;
                border-radius: 12px;
                margin: 6px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Agri Broker AI Market Summary</h1>
            <p>Generated from your current Supabase marketplace data.</p>

            <div>
                <span class="stat">Active: {snapshot.get("active_requests", 0)}</span>
                <span class="stat">Sell: {snapshot.get("active_sell_requests", 0)}</span>
                <span class="stat">Buy: {snapshot.get("active_buy_requests", 0)}</span>
                <span class="stat">Deals: {snapshot.get("confirmed_deals", 0)}</span>
                <span class="stat">Risk Queue: {snapshot.get("untrusted_items", 0)}</span>
                <span class="stat">Fraud Reports: {snapshot.get("fraud_reports", 0)}</span>
            </div>
        </div>

        <div class="card">
            <h2>AI Summary</h2>
            <pre>{summary}</pre>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(html)