from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware

from app.routers import whatsapp
from app.routers import dashboard
from app.routers import cron
from app.routers import admin_ai
from app.routers import web_app
from app.routers import portfolio
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.core.rate_limit import limiter

app = FastAPI(title="Agri Broker API")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(whatsapp.router)
app.include_router(dashboard.router)
app.include_router(cron.router)
app.include_router(admin_ai.router)
app.include_router(web_app.router)
app.include_router(portfolio.router)


@app.get("/")
def root():
    return {"status": "running", "message": "Agri Broker API is live"}