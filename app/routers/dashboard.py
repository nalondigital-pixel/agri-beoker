from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.db.supabase_client import supabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request):
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