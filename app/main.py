from fastapi import FastAPI

from app.routers import whatsapp
from app.routers import dashboard
from app.db.supabase_client import supabase
from app.routers import cron

app = FastAPI(title="Agri Broker API")

app.include_router(whatsapp.router)
app.include_router(dashboard.router)
app.include_router(cron.router)


@app.get("/")
def root():
    return {"status": "running", "message": "Agri Broker API is live"}


@app.get("/debug/buyers")
def debug_buyers():
    res = supabase.table("buyers").select("*").execute()
    return res.data