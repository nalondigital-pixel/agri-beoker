from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import DASHBOARD_PASSWORD
from app.db.supabase_client import supabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def dashboard_login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None},
    )


@router.post("/login")
def dashboard_login(password: str = Form(...)):
    if password == DASHBOARD_PASSWORD:
        response = RedirectResponse(url="/dashboard/", status_code=302)
        response.set_cookie(
            key="dashboard_auth",
            value="ok",
            httponly=True,
            max_age=60 * 60 * 12,
        )
        return response

    return RedirectResponse(url="/dashboard/login?error=1", status_code=302)


@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request):
    if request.cookies.get("dashboard_auth") != "ok":
        return RedirectResponse(url="/dashboard/login", status_code=302)

    listings = supabase.table("listings").select("*").order("created_at", desc=True).execute().data or []
    buyers = supabase.table("buyers").select("*").order("created_at", desc=True).execute().data or []
    deals = supabase.table("deals").select("*").order("created_at", desc=True).execute().data or []
    blocked_users = supabase.table("blocked_users").select("*").order("created_at", desc=True).execute().data or []
    fraud_reports = supabase.table("fraud_reports").select("*").order("created_at", desc=True).execute().data or []
    unknown_terms = supabase.table("unknown_terms").select("*").order("count", desc=True).execute().data or []

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "listings": listings,
            "buyers": buyers,
            "deals": deals,
            "blocked_users": blocked_users,
            "fraud_reports": fraud_reports,
            "unknown_terms": unknown_terms,
        },
    )