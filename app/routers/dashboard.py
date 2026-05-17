from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.config import DASHBOARD_PASSWORD
from app.db.supabase_client import supabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def is_logged_in(request: Request):
    return request.cookies.get("dashboard_auth") == "true"


def redirect_to_login():
    return RedirectResponse(url="/dashboard/login", status_code=302)


@router.get("/ping")
def dashboard_ping():
    return {"status": "dashboard router working"}


def safe_fetch(table_name: str, limit: int = 100):
    try:
        response = supabase.table(table_name).select("*").limit(limit).execute()
        return response.data or []
    except Exception as e:
        print(f"Dashboard fetch failed for {table_name}:", e)
        return []


def get_dashboard_data():
    listings = safe_fetch("listings")
    deals = safe_fetch("deals")
    profiles = safe_fetch("user_profiles")
    blocked_users = safe_fetch("blocked_users")
    fraud_reports = safe_fetch("fraud_reports")
    untrusted_queue = safe_fetch("untrusted_queue")

    active_requests = [
        item for item in listings
        if item.get("status") == "active"
    ]

    closed_requests = [
        item for item in listings
        if item.get("status") in ["fulfilled", "cancelled", "closed", "matched", "expired"]
    ]
    

    return {
        "listings": listings,
        "active_requests": active_requests,
        "closed_requests": closed_requests,
        "deals": deals,
        "profiles": profiles,
        "blocked_users": blocked_users,
        "fraud_reports": fraud_reports,
        "untrusted_queue": untrusted_queue,
        "stats": {
            "total_requests": len(listings),
            "active_requests": len(active_requests),
            "closed_requests": len(closed_requests),
            "deals": len(deals),
            "users": len(profiles),
            "fraud_reports": len(fraud_reports),
            "untrusted_cases": len(untrusted_queue),
        },
    }


@router.get("/debug-data")
def debug_dashboard_data():
    return get_dashboard_data()


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agri Broker Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f7f3;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }
            .card {
                background: white;
                padding: 30px;
                border-radius: 14px;
                box-shadow: 0 3px 14px rgba(0,0,0,0.08);
                width: 360px;
            }
            h1 {
                color: #1f7a3f;
                margin-top: 0;
            }
            input, button {
                width: 100%;
                padding: 12px;
                margin-top: 12px;
                box-sizing: border-box;
                border-radius: 8px;
                border: 1px solid #ccc;
            }
            button {
                background: #1f7a3f;
                color: white;
                font-weight: bold;
                border: none;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Agri Broker</h1>
            <p>Admin Dashboard Login</p>

            <form method="post" action="/dashboard/login">
                <input type="password" name="password" placeholder="Dashboard password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """


@router.post("/login")
def login(password: str = Form(...)):
    if password != DASHBOARD_PASSWORD:
        return HTMLResponse("""
        <h2>Invalid password</h2>
        <p><a href="/dashboard/login">Try again</a></p>
        """, status_code=401)

    response = RedirectResponse(url="/dashboard/", status_code=302)
    response.set_cookie(
        key="dashboard_auth",
        value="true",
        httponly=True,
        max_age=60 * 60 * 12,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/dashboard/login", status_code=302)
    response.delete_cookie("dashboard_auth")
    return response


@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request):
    if not is_logged_in(request):
        return redirect_to_login()

    data = get_dashboard_data()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agri Broker Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f7f3;
                margin: 0;
                color: #1f2933;
            }
            header {
                background: #1f7a3f;
                color: white;
                padding: 18px 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            header h1 {
                margin: 0;
            }
            header a {
                color: white;
                font-weight: bold;
                text-decoration: none;
            }
            .container {
                padding: 24px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
                gap: 16px;
                margin-bottom: 28px;
            }
            .card, section {
                background: white;
                border-radius: 12px;
                padding: 18px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }
            section {
                margin-bottom: 28px;
            }
            h2 {
                color: #1f7a3f;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            th, td {
                border-bottom: 1px solid #eee;
                padding: 9px;
                text-align: left;
                font-size: 13px;
            }
            th {
                background: #f0f7ef;
            }
            .table-wrap {
                overflow-x: auto;
            }
            button {
                border: none;
                padding: 7px 10px;
                border-radius: 7px;
                font-weight: bold;
                cursor: pointer;
            }
            .green { background: #1f7a3f; color: white; }
            .yellow { background: #fdb022; color: #111; }
            .red { background: #d92d20; color: white; }
            .phone {
                font-family: Consolas, monospace;
            }
        </style>
    </head>
    <body>
        <header>
            <h1>Agri Broker Dashboard</h1>
            <a href="/dashboard/logout">Logout</a>
        </header>

        <div class="container">
            <div class="stats">
    """

    stats = data["stats"]

    for label, value in stats.items():
        html += f"""
                <div class="card">
                    <h3>{label.replace("_", " ").title()}</h3>
                    <h1>{value}</h1>
                </div>
        """

    html += """
            </div>
    """

    html += build_requests_section("📌 Active Requests", data["active_requests"], active=True)
    html += build_requests_section("✅ Closed Requests", data["closed_requests"], active=False)
    html += build_deals_section(data["deals"])
    html += build_users_section(data["profiles"])
    html += build_untrusted_section(data["untrusted_queue"])
    html += build_fraud_section(data["fraud_reports"])

    html += """
        </div>
    </body>
    </html>
    """

    return html


def build_requests_section(title, requests, active: bool):
    html = f"""
    <section>
        <h2>{title}</h2>
    """

    if not requests:
        html += "<p>No records.</p></section>"
        return html

    html += """
        <div class="table-wrap">
        <table>
            <tr>
                <th>Intent</th>
                <th>Commodity</th>
                <th>Quantity</th>
                <th>Location</th>
                <th>Phone</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
    """

    for item in requests:
        listing_id = item.get("id", "")
        quantity = f"{item.get('quantity', '')} {item.get('unit', '')}".strip()

        html += f"""
            <tr>
                <td>{item.get("intent", "")}</td>
                <td>{item.get("commodity", "")}</td>
                <td>{quantity}</td>
                <td>{item.get("location", "")}</td>
                <td class="phone">{item.get("seller_phone", "")}</td>
                <td>{item.get("status", "")}</td>
                <td>
        """

        if active:
            html += f"""
                    <form method="post" action="/dashboard/requests/close" style="display:inline;">
                        <input type="hidden" name="listing_id" value="{listing_id}">
                        <input type="hidden" name="status" value="fulfilled">
                        <button class="green" type="submit">Fulfilled</button>
                    </form>

                    <form method="post" action="/dashboard/requests/close" style="display:inline;">
                        <input type="hidden" name="listing_id" value="{listing_id}">
                        <input type="hidden" name="status" value="cancelled">
                        <button class="yellow" type="submit">Cancel</button>
                    </form>
            """
        else:
            html += f"""
                    <form method="post" action="/dashboard/requests/reactivate" style="display:inline;">
                        <input type="hidden" name="listing_id" value="{listing_id}">
                        <button class="green" type="submit">Reactivate</button>
                    </form>
            """

        html += """
                </td>
            </tr>
        """

    html += """
        </table>
        </div>
    </section>
    """

    return html


def build_deals_section(deals):
    html = """
    <section>
        <h2>🤝 Deals & Feedback</h2>
    """

    if not deals:
        html += "<p>No deals yet.</p></section>"
        return html

    html += """
        <div class="table-wrap">
        <table>
            <tr>
                <th>Status</th>
                <th>Buyer</th>
                <th>Seller</th>
                <th>Buyer Feedback</th>
                <th>Seller Feedback</th>
                <th>Created</th>
            </tr>
    """

    for deal in deals:
        html += f"""
            <tr>
                <td>{deal.get("status", "")}</td>
                <td class="phone">{deal.get("buyer_phone", "")}</td>
                <td class="phone">{deal.get("seller_phone", "")}</td>
                <td>{deal.get("buyer_feedback", "")}</td>
                <td>{deal.get("seller_feedback", "")}</td>
                <td>{deal.get("created_at", "")}</td>
            </tr>
        """

    html += "</table></div></section>"
    return html


def build_users_section(users):
    html = """
    <section>
        <h2>👤 Registered Users</h2>
    """

    if not users:
        html += "<p>No users yet.</p></section>"
        return html

    html += """
        <div class="table-wrap">
        <table>
            <tr>
                <th>Phone</th>
                <th>Name</th>
                <th>City</th>
                <th>Area</th>
                <th>Verified</th>
                <th>Trust</th>
                <th>Actions</th>
            </tr>
    """

    for user in users:
        phone = user.get("phone", "")

        html += f"""
            <tr>
                <td class="phone">{phone}</td>
                <td>{user.get("name", "")}</td>
                <td>{user.get("city", "")}</td>
                <td>{user.get("neighborhood", "")}</td>
                <td>{user.get("verified", "")}</td>
                <td>{user.get("trust_score", "")} {user.get("trust_rank", "")}</td>
                <td>
                    <form method="post" action="/dashboard/profiles/verify" style="display:inline;">
                        <input type="hidden" name="phone" value="{phone}">
                        <button class="green" type="submit">Verify</button>
                    </form>

                    <form method="post" action="/dashboard/profiles/block" style="display:inline;">
                        <input type="hidden" name="phone" value="{phone}">
                        <input type="hidden" name="reason" value="Blocked from dashboard">
                        <button class="red" type="submit">Block</button>
                    </form>
                </td>
            </tr>
        """

    html += "</table></div></section>"
    return html


def build_untrusted_section(cases):
    html = """
    <section>
        <h2>⚠️ Untrusted Queue</h2>
    """

    if not cases:
        html += "<p>No untrusted cases.</p></section>"
        return html

    html += """
        <div class="table-wrap">
        <table>
            <tr>
                <th>Status</th>
                <th>Reporter</th>
                <th>Reported</th>
                <th>Reason</th>
                <th>Actions</th>
            </tr>
    """

    for case in cases:
        case_id = case.get("id", "")
        reported_phone = case.get("reported_phone", "")

        html += f"""
            <tr>
                <td>{case.get("status", "")}</td>
                <td class="phone">{case.get("reporter_phone", "")}</td>
                <td class="phone">{reported_phone}</td>
                <td>{case.get("reason", "")}</td>
                <td>
                    <form method="post" action="/dashboard/untrusted/resolve" style="display:inline;">
                        <input type="hidden" name="case_id" value="{case_id}">
                        <button class="green" type="submit">Resolve</button>
                    </form>

                    <form method="post" action="/dashboard/untrusted/block" style="display:inline;">
                        <input type="hidden" name="case_id" value="{case_id}">
                        <input type="hidden" name="reported_phone" value="{reported_phone}">
                        <button class="red" type="submit">Block</button>
                    </form>
                </td>
            </tr>
        """

    html += "</table></div></section>"
    return html


def build_fraud_section(reports):
    html = """
    <section>
        <h2>🚨 Fraud Reports</h2>
    """

    if not reports:
        html += "<p>No fraud reports.</p></section>"
        return html

    html += """
        <div class="table-wrap">
        <table>
            <tr>
                <th>Status</th>
                <th>Reporter</th>
                <th>Reported</th>
                <th>Reason</th>
                <th>Action</th>
            </tr>
    """

    for report in reports:
        report_id = report.get("id", "")

        html += f"""
            <tr>
                <td>{report.get("status", "")}</td>
                <td class="phone">{report.get("reporter_phone", "")}</td>
                <td class="phone">{report.get("reported_phone", "")}</td>
                <td>{report.get("reason", "")}</td>
                <td>
                    <form method="post" action="/dashboard/fraud/resolve">
                        <input type="hidden" name="report_id" value="{report_id}">
                        <button class="green" type="submit">Resolve</button>
                    </form>
                </td>
            </tr>
        """

    html += "</table></div></section>"
    return html


@router.post("/requests/close")
def close_request(
    request: Request,
    listing_id: str = Form(...),
    status: str = Form(...),
):
    if not is_logged_in(request):
        return redirect_to_login()

    if status not in ["fulfilled", "cancelled", "closed", "expired"]:
        return RedirectResponse(url="/dashboard/", status_code=302)

    supabase.table("listings").update({
        "status": status,
    }).eq("id", listing_id).execute()

    return RedirectResponse(url="/dashboard/", status_code=302)


@router.post("/requests/reactivate")
def reactivate_request(
    request: Request,
    listing_id: str = Form(...),
):
    if not is_logged_in(request):
        return redirect_to_login()

    supabase.table("listings").update({
        "status": "active",
    }).eq("id", listing_id).execute()

    return RedirectResponse(url="/dashboard/", status_code=302)


@router.post("/profiles/verify")
def verify_profile(
    request: Request,
    phone: str = Form(...),
):
    if not is_logged_in(request):
        return redirect_to_login()

    supabase.table("user_profiles").update({
        "verified": True,
        "trust_score": 60,
        "trust_rank": "Reliable User",
    }).eq("phone", phone).execute()

    return RedirectResponse(url="/dashboard/", status_code=302)


@router.post("/profiles/block")
def block_profile(
    request: Request,
    phone: str = Form(...),
    reason: str = Form("Blocked from dashboard"),
):
    if not is_logged_in(request):
        return redirect_to_login()

    supabase.table("blocked_users").upsert({
        "phone": phone,
        "reason": reason,
    }, on_conflict="phone").execute()

    return RedirectResponse(url="/dashboard/", status_code=302)


@router.post("/fraud/resolve")
def resolve_fraud_report(
    request: Request,
    report_id: str = Form(...),
):
    if not is_logged_in(request):
        return redirect_to_login()

    supabase.table("fraud_reports").update({
        "status": "resolved",
    }).eq("id", report_id).execute()

    return RedirectResponse(url="/dashboard/", status_code=302)


@router.post("/untrusted/resolve")
def resolve_untrusted_case(
    request: Request,
    case_id: str = Form(...),
):
    if not is_logged_in(request):
        return redirect_to_login()

    supabase.table("untrusted_queue").update({
        "status": "resolved",
    }).eq("id", case_id).execute()

    return RedirectResponse(url="/dashboard/", status_code=302)


@router.post("/untrusted/block")
def block_untrusted_user(
    request: Request,
    case_id: str = Form(...),
    reported_phone: str = Form(...),
):
    if not is_logged_in(request):
        return redirect_to_login()

    supabase.table("blocked_users").upsert({
        "phone": reported_phone,
        "reason": "Blocked from untrusted queue review",
    }, on_conflict="phone").execute()

    supabase.table("untrusted_queue").update({
        "status": "blocked",
    }).eq("id", case_id).execute()

    return RedirectResponse(url="/dashboard/", status_code=302)