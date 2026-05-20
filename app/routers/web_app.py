import re
from html import escape

from fastapi import APIRouter, Form, Request
from app.core.rate_limit import limiter
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.services.db_service import save_listing
from app.services.transporter_service import register_or_update_transporter
from app.services.location_normalizer_service import normalize_location_name
from app.services.ai_assistant_service import generate_ai_assistant_reply
from app.db.supabase_client import supabase


router = APIRouter(prefix="/web", tags=["Public Web App"])


class WebChatRequest(BaseModel):
    message: str


ALLOWED_UNITS = ["kg", "bags", "boxes", "crates", ""]
ALLOWED_CURRENCIES = ["USD", "ZIG", "ZAR"]
ALLOWED_SELL_DELIVERY_OPTIONS = ["unknown", "can_deliver", "buyer_collects", "needs_transport"]
ALLOWED_BUY_DELIVERY_OPTIONS = ["unknown", "will_collect", "needs_transport"]
ALLOWED_CAPACITY_UNITS = ["kg", "tonnes", "boxes", "bags"]


def clean_text(value: str, field_name: str, max_length: int, required: bool = True):
    value = str(value or "").strip()

    if required and not value:
        raise ValueError(f"{field_name} is required.")

    if len(value) > max_length:
        raise ValueError(f"{field_name} is too long. Maximum allowed is {max_length} characters.")

    blocked_patterns = [
        "<script",
        "</script",
        "javascript:",
        "onerror=",
        "onload=",
    ]

    lower_value = value.lower()

    for pattern in blocked_patterns:
        if pattern in lower_value:
            raise ValueError(f"{field_name} contains unsafe content.")

    return value


def clean_phone(phone: str):
    phone = str(phone or "").strip()
    phone = phone.replace(" ", "").replace("-", "").replace("+", "")

    if not phone:
        raise ValueError("Phone number is required.")

    if not phone.isdigit():
        raise ValueError("Phone number must contain digits only.")

    if len(phone) < 9 or len(phone) > 15:
        raise ValueError("Phone number length is invalid.")

    return phone


def validate_positive_number(value, field_name: str, max_value: float = 100000000):
    try:
        number = float(value)
    except Exception:
        raise ValueError(f"{field_name} must be a valid number.")

    if number <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    if number > max_value:
        raise ValueError(f"{field_name} is unrealistically large.")

    return number


def validate_optional_price(value):
    value = str(value or "").strip()

    if not value:
        return None

    try:
        price = float(value)
    except Exception:
        raise ValueError("Price must be a valid number.")

    if price < 0:
        raise ValueError("Price cannot be negative.")

    if price > 100000000:
        raise ValueError("Price is unrealistically large.")

    return price


def validate_choice(value: str, allowed_values: list, field_name: str):
    value = str(value or "").strip()

    if value not in allowed_values:
        raise ValueError(f"{field_name} has an invalid value.")

    return value


def validation_error(message: str):
    body = f"""
    <section class="success" style="border-color: rgba(248,113,113,0.45); background: rgba(127,29,29,0.22); color: #fecaca;">
        <h2>Invalid submission</h2>
        <p>{escape(message)}</p>
    </section>

    <section class="card">
        <h3>What to do</h3>
        <p class="muted">
            Please go back and check your form details. Make sure numbers are positive,
            phone numbers contain digits only, and text fields are not too long.
        </p>

        <div class="actions">
            <a class="button" href="/web">Back Home</a>
        </div>
    </section>
    """

    return HTMLResponse(page_layout("Invalid Submission", body), status_code=400)


def icon(name: str):
    icons = {
        "leaf": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M5 21C5 13 10 5 21 3C19 14 13 19 5 21Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M5 21C8 14 12 10 17 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """,
        "store": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 10L5.5 4H18.5L20 10" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M5 10V20H19V10" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M9 20V14H15V20" stroke="currentColor" stroke-width="2"/>
            <path d="M4 10C4.5 12 7.5 12 8 10C8.5 12 11.5 12 12 10C12.5 12 15.5 12 16 10C16.5 12 19.5 12 20 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """,
        "cart": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M3 4H5L7.5 15H18.5L21 7H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="9" cy="20" r="1.5" stroke="currentColor" stroke-width="2"/>
            <circle cx="18" cy="20" r="1.5" stroke="currentColor" stroke-width="2"/>
        </svg>
        """,
        "truck": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M3 6H15V17H3V6Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M15 10H19L22 13V17H15V10Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <circle cx="7" cy="19" r="2" stroke="currentColor" stroke-width="2"/>
            <circle cx="18" cy="19" r="2" stroke="currentColor" stroke-width="2"/>
        </svg>
        """,
        "brain": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M9 4C6.8 4 5 5.8 5 8C3.8 8.7 3 10 3 11.5C3 13.3 4.2 14.9 5.8 15.4C6.1 18 8.3 20 11 20H13C15.7 20 17.9 18 18.2 15.4C19.8 14.9 21 13.3 21 11.5C21 10 20.2 8.7 19 8C19 5.8 17.2 4 15 4C13.8 4 12.7 4.5 12 5.4C11.3 4.5 10.2 4 9 4Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M12 5.5V20" stroke="currentColor" stroke-width="2"/>
            <path d="M8 10H12M16 10H12M8 14H12M16 14H12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """,
        "target": """
        <svg viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="2"/>
            <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="2"/>
            <circle cx="12" cy="12" r="1" stroke="currentColor" stroke-width="2"/>
        </svg>
        """,
        "shield": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 3L20 6V11C20 16 16.5 20 12 21C7.5 20 4 16 4 11V6L12 3Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M8.5 12L11 14.5L16 9.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """,
        "chart": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 19V5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M4 19H20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M8 16V11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M12 16V8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M16 16V13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """,
        "bolt": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M13 2L4 14H11L10 22L20 9H13L13 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
        </svg>
        """,
        "globe": """
        <svg viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/>
            <path d="M3 12H21" stroke="currentColor" stroke-width="2"/>
            <path d="M12 3C15 6 15 18 12 21C9 18 9 6 12 3Z" stroke="currentColor" stroke-width="2"/>
        </svg>
        """,
        "send": """
        <svg viewBox="0 0 24 24" fill="none">
            <path d="M21 3L10 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M21 3L14 21L10 14L3 10L21 3Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
        </svg>
        """,
    }

    return f'<span class="svg-icon">{icons.get(name, icons["leaf"])}</span>'


@router.post("/chat")
@limiter.limit("10/minute")
def web_chat(http_request: Request, request: WebChatRequest):
    user_message = (request.message or "").strip()

    if not user_message:
        return {"reply": "Please type a question first."}

    try:
        reply = generate_ai_assistant_reply(
            user_message=user_message,
            user_name="website visitor",
            user_language="english",
        )
        return {"reply": reply}
    except Exception as e:
        print("Web chatbot error:", e)
        return {
            "reply": (
                "I can help with Agri Broker, buying, selling, transporter registration, "
                "and how the platform works. Please try asking again."
            )
        }


def page_layout(title: str, body: str):
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>__TITLE__</title>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />

        <style>
            :root {
                --bg: #07111f;
                --card: rgba(255,255,255,0.08);
                --text: #eaf2ff;
                --muted: #9fb0c8;
                --primary: #16a34a;
                --primary-2: #22c55e;
                --accent: #38bdf8;
                --purple: #7c3aed;
                --border: rgba(255,255,255,0.12);
                --shadow: 0 20px 60px rgba(0,0,0,0.35);
                --radius: 22px;
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            html {
                scroll-behavior: smooth;
            }

            body {
                font-family: Inter, Arial, sans-serif;
                background:
                    radial-gradient(circle at 10% 20%, rgba(34,197,94,0.14), transparent 25%),
                    radial-gradient(circle at 90% 10%, rgba(56,189,248,0.14), transparent 20%),
                    radial-gradient(circle at 80% 80%, rgba(124,58,237,0.10), transparent 20%),
                    linear-gradient(135deg, #06101d 0%, #0a1424 45%, #0d1a2d 100%);
                color: var(--text);
                min-height: 100vh;
                overflow-x: hidden;
            }

            .bg-orb {
                position: fixed;
                width: 320px;
                height: 320px;
                border-radius: 50%;
                filter: blur(70px);
                opacity: 0.35;
                z-index: 0;
                animation: floatBlob 14s ease-in-out infinite;
                pointer-events: none;
            }

            .orb-1 {
                top: -80px;
                left: -90px;
                background: #22c55e;
            }

            .orb-2 {
                top: 120px;
                right: -100px;
                background: #38bdf8;
                animation-delay: 2s;
            }

            .orb-3 {
                bottom: -100px;
                left: 25%;
                background: #7c3aed;
                animation-delay: 4s;
            }

            @keyframes floatBlob {
                0%,100% { transform: translateY(0px) translateX(0px) scale(1); }
                50% { transform: translateY(18px) translateX(12px) scale(1.05); }
            }

            .svg-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 20px;
                height: 20px;
                color: currentColor;
                flex-shrink: 0;
            }

            .svg-icon svg {
                width: 100%;
                height: 100%;
                display: block;
            }

            .nav-wrap {
                position: sticky;
                top: 0;
                z-index: 50;
                backdrop-filter: blur(16px);
                background: rgba(7,17,31,0.65);
                border-bottom: 1px solid rgba(255,255,255,0.08);
            }

            .nav {
                max-width: 1200px;
                margin: 0 auto;
                padding: 18px 24px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 20px;
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 22px;
                font-weight: 800;
                color: white;
                text-decoration: none;
                letter-spacing: -0.4px;
            }

            .brand-badge {
                width: 42px;
                height: 42px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border-radius: 14px;
                background: linear-gradient(135deg, var(--primary), var(--accent));
                box-shadow: 0 10px 30px rgba(34,197,94,0.35);
                color: white;
            }

            .brand-badge .svg-icon {
                width: 24px;
                height: 24px;
            }

            .nav-links {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }

            .nav-links a {
                color: #dbeafe;
                text-decoration: none;
                padding: 10px 14px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 600;
                transition: all 0.25s ease;
            }

            .nav-links a:hover {
                background: rgba(255,255,255,0.08);
                transform: translateY(-2px);
                color: white;
            }

            .container {
                position: relative;
                z-index: 1;
                max-width: 1200px;
                margin: 0 auto;
                padding: 30px 24px 50px;
            }

            .hero {
                position: relative;
                overflow: hidden;
                padding: 56px 36px;
                border-radius: 30px;
                background:
                    linear-gradient(135deg, rgba(22,163,74,0.95), rgba(34,197,94,0.75) 45%, rgba(56,189,248,0.75) 100%);
                box-shadow: var(--shadow);
                margin-bottom: 28px;
                isolation: isolate;
                animation: fadeUp 0.8s ease;
            }

            .hero h1 {
                font-size: clamp(34px, 5vw, 58px);
                line-height: 1.02;
                letter-spacing: -1.2px;
                margin-bottom: 16px;
                color: white;
                max-width: 780px;
            }

            .hero p {
                max-width: 780px;
                line-height: 1.7;
                font-size: 18px;
                color: rgba(255,255,255,0.92);
            }

            .actions {
                display: flex;
                flex-wrap: wrap;
                gap: 14px;
                margin-top: 28px;
            }

            .button {
                position: relative;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 9px;
                text-decoration: none;
                padding: 14px 20px;
                border-radius: 16px;
                font-weight: 700;
                font-size: 15px;
                border: none;
                cursor: pointer;
                color: white;
                background: linear-gradient(135deg, var(--primary), var(--primary-2));
                box-shadow: 0 12px 30px rgba(22,163,74,0.28);
                transition: transform 0.25s ease, box-shadow 0.25s ease, filter 0.25s ease;
                overflow: hidden;
            }

            .button:hover {
                transform: translateY(-4px) scale(1.03);
                box-shadow: 0 18px 36px rgba(22,163,74,0.38);
                filter: brightness(1.05);
            }

            .button.secondary {
                background: rgba(255,255,255,0.14);
                color: white;
                border: 1px solid rgba(255,255,255,0.22);
                box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            }

            .stats {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 16px;
                margin: 26px 0 10px;
            }

            .stat {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 18px;
                padding: 18px;
                backdrop-filter: blur(12px);
                animation: fadeUp 0.9s ease;
            }

            .stat .num {
                font-size: 28px;
                font-weight: 800;
                color: white;
                margin-bottom: 6px;
            }

            .stat .label {
                font-size: 13px;
                color: rgba(255,255,255,0.82);
            }

            .section-title {
                font-size: 30px;
                letter-spacing: -0.8px;
                margin-bottom: 8px;
                color: white;
            }

            .section-subtitle {
                color: var(--muted);
                margin-bottom: 22px;
                line-height: 1.7;
            }

            .grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 20px;
                margin-top: 18px;
            }

            .grid-2 {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 20px;
            }

            .card {
                background: rgba(255,255,255,0.08);
                border: 1px solid var(--border);
                backdrop-filter: blur(16px);
                border-radius: var(--radius);
                padding: 24px;
                box-shadow: var(--shadow);
                transition: transform 0.3s ease, box-shadow 0.3s ease, border 0.3s ease;
                animation: fadeUp 0.8s ease;
            }

            .card:hover {
                transform: translateY(-8px);
                box-shadow: 0 24px 60px rgba(0,0,0,0.42);
                border-color: rgba(255,255,255,0.18);
            }

            .card h2,
            .card h3 {
                color: white;
                margin-bottom: 12px;
                letter-spacing: -0.5px;
            }

            .card p,
            .muted {
                color: var(--muted);
                line-height: 1.75;
                font-size: 15px;
            }

            .icon-box {
                width: 54px;
                height: 54px;
                border-radius: 16px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 16px;
                background: linear-gradient(135deg, rgba(34,197,94,0.18), rgba(56,189,248,0.18));
                border: 1px solid rgba(255,255,255,0.12);
                color: #dbeafe;
            }

            .icon-box .svg-icon {
                width: 28px;
                height: 28px;
            }

            .success {
                background: linear-gradient(135deg, rgba(22,163,74,0.20), rgba(34,197,94,0.12));
                border: 1px solid rgba(34,197,94,0.32);
                padding: 20px;
                border-radius: 20px;
                color: #d1fae5;
                margin-bottom: 22px;
                box-shadow: 0 18px 40px rgba(0,0,0,0.20);
                animation: fadeUp 0.7s ease;
            }

            .badge {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 10px 14px;
                border-radius: 999px;
                margin: 6px 8px 0 0;
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.1);
                color: #dbeafe;
                font-size: 13px;
                font-weight: 700;
                transition: transform 0.25s ease, background 0.25s ease;
            }

            .badge .svg-icon {
                width: 16px;
                height: 16px;
            }

            .badge:hover {
                transform: translateY(-3px);
                background: rgba(255,255,255,0.12);
            }

            form {
                margin-top: 8px;
            }

            .field-row {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 18px;
            }

            label {
                display: block;
                font-size: 13px;
                font-weight: 700;
                color: #dbeafe;
                margin-bottom: 8px;
                letter-spacing: 0.2px;
            }

            input,
            select,
            textarea {
                width: 100%;
                padding: 14px 15px;
                border-radius: 16px;
                border: 1px solid rgba(255,255,255,0.12);
                background: rgba(255,255,255,0.06);
                color: white;
                font-size: 15px;
                outline: none;
                transition: all 0.25s ease;
                margin-bottom: 16px;
            }

            input::placeholder,
            textarea::placeholder {
                color: #8fa3be;
            }

            select option {
                color: black;
            }

            input:focus,
            select:focus,
            textarea:focus {
                border-color: rgba(56,189,248,0.55);
                box-shadow: 0 0 0 4px rgba(56,189,248,0.14);
                transform: translateY(-1px);
            }

            textarea {
                min-height: 110px;
                resize: vertical;
            }

            .footer {
                padding: 24px;
                text-align: center;
                color: #8fa3be;
                font-size: 14px;
            }

            .reveal {
                opacity: 0;
                transform: translateY(18px);
                transition: all 0.7s ease;
            }

            .reveal.visible {
                opacity: 1;
                transform: translateY(0);
            }

            @keyframes fadeUp {
                from {
                    opacity: 0;
                    transform: translateY(24px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .chatbot-launcher {
                position: fixed;
                right: 24px;
                bottom: 24px;
                z-index: 100;
                width: 62px;
                height: 62px;
                border-radius: 22px;
                border: 1px solid rgba(255,255,255,0.18);
                background: linear-gradient(135deg, var(--primary), var(--accent));
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 18px 40px rgba(0,0,0,0.35);
                cursor: pointer;
                transition: transform 0.25s ease, box-shadow 0.25s ease;
            }

            .chatbot-launcher:hover {
                transform: translateY(-5px) scale(1.05);
                box-shadow: 0 24px 50px rgba(34,197,94,0.35);
            }

            .chatbot-launcher .svg-icon {
                width: 28px;
                height: 28px;
            }

            .chatbot-panel {
                position: fixed;
                right: 24px;
                bottom: 100px;
                z-index: 100;
                width: 380px;
                max-width: calc(100vw - 32px);
                height: 520px;
                max-height: calc(100vh - 140px);
                background: rgba(7,17,31,0.92);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 26px;
                box-shadow: 0 28px 80px rgba(0,0,0,0.48);
                backdrop-filter: blur(22px);
                overflow: hidden;
                display: none;
                flex-direction: column;
                animation: chatPop 0.28s ease;
            }

            .chatbot-panel.open {
                display: flex;
            }

            @keyframes chatPop {
                from {
                    opacity: 0;
                    transform: translateY(14px) scale(0.96);
                }
                to {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            .chatbot-header {
                padding: 18px;
                background: linear-gradient(135deg, rgba(22,163,74,0.9), rgba(56,189,248,0.7));
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
            }

            .chatbot-title {
                display: flex;
                align-items: center;
                gap: 10px;
                font-weight: 800;
                color: white;
            }

            .chatbot-close {
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.18);
                color: white;
                width: 34px;
                height: 34px;
                border-radius: 12px;
                cursor: pointer;
                font-size: 18px;
            }

            .chatbot-messages {
                flex: 1;
                padding: 16px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .chat-message {
                padding: 12px 14px;
                border-radius: 16px;
                line-height: 1.55;
                font-size: 14px;
                max-width: 86%;
                white-space: pre-wrap;
            }

            .chat-message.bot {
                background: rgba(255,255,255,0.08);
                color: #dbeafe;
                border: 1px solid rgba(255,255,255,0.08);
                align-self: flex-start;
            }

            .chat-message.user {
                background: linear-gradient(135deg, var(--primary), var(--primary-2));
                color: white;
                align-self: flex-end;
            }

            .chatbot-suggestions {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                padding: 0 16px 12px;
            }

            .chatbot-suggestion {
                background: rgba(255,255,255,0.08);
                color: #dbeafe;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 999px;
                padding: 8px 10px;
                font-size: 12px;
                cursor: pointer;
            }

            .chatbot-input-row {
                padding: 14px;
                border-top: 1px solid rgba(255,255,255,0.10);
                display: flex;
                gap: 10px;
            }

            .chatbot-input-row input {
                margin-bottom: 0;
                border-radius: 14px;
            }

            .chatbot-send {
                min-width: 52px;
                border-radius: 14px;
                border: none;
                background: linear-gradient(135deg, var(--primary), var(--accent));
                color: white;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }

            .chatbot-send .svg-icon {
                width: 20px;
                height: 20px;
            }

            .typing {
                opacity: 0.75;
                font-style: italic;
            }

            @media (max-width: 980px) {
                .grid {
                    grid-template-columns: 1fr 1fr;
                }

                .stats {
                    grid-template-columns: 1fr 1fr;
                }
            }

            @media (max-width: 760px) {
                .nav {
                    flex-direction: column;
                    align-items: flex-start;
                }

                .grid,
                .grid-2,
                .field-row,
                .stats {
                    grid-template-columns: 1fr;
                }

                .hero {
                    padding: 38px 24px;
                }

                .hero h1 {
                    font-size: 34px;
                }

                .container {
                    padding: 22px 16px 40px;
                }

                .nav-links {
                    width: 100%;
                }

                .chatbot-panel {
                    right: 16px;
                    bottom: 92px;
                    height: 500px;
                }

                .chatbot-launcher {
                    right: 16px;
                    bottom: 18px;
                }
            }
        </style>
    </head>

    <body>
        <div class="bg-orb orb-1"></div>
        <div class="bg-orb orb-2"></div>
        <div class="bg-orb orb-3"></div>

        <div class="nav-wrap">
            <div class="nav">
                <a class="brand" href="/web">
                    <span class="brand-badge">__ICON_LEAF__</span>
                    <span>Agri Broker</span>
                </a>

                <div class="nav-links">
                    <a href="/web">Home</a>
                    <a href="/web/sell">Sell</a>
                    <a href="/web/buy">Buy</a>
                    <a href="/web/transporter">Transporter</a>
                </div>
            </div>
        </div>

        <div class="container">
            __BODY__
        </div>

        <div class="chatbot-panel" id="chatbotPanel">
            <div class="chatbot-header">
                <div class="chatbot-title">
                    __ICON_BRAIN__
                    <span>Agri Broker AI</span>
                </div>
                <button class="chatbot-close" onclick="toggleChatbot()">×</button>
            </div>

            <div class="chatbot-messages" id="chatMessages">
                <div class="chat-message bot">
                    Hi, I am the Agri Broker AI assistant. Ask me how the platform works, how to buy, sell, or register as a transporter.
                </div>
            </div>

            <div class="chatbot-suggestions">
                <button class="chatbot-suggestion" onclick="sendSuggestion('How does Agri Broker work?')">How it works</button>
                <button class="chatbot-suggestion" onclick="sendSuggestion('How do I sell produce?')">Selling</button>
                <button class="chatbot-suggestion" onclick="sendSuggestion('How do transporters get jobs?')">Transporters</button>
            </div>

            <div class="chatbot-input-row">
                <input id="chatInput" placeholder="Ask about Agri Broker..." onkeydown="handleChatKey(event)" />
                <button class="chatbot-send" onclick="sendChatMessage()">__ICON_SEND__</button>
            </div>
        </div>

        <button class="chatbot-launcher" onclick="toggleChatbot()" aria-label="Open AI assistant">
            __ICON_BRAIN__
        </button>

        <div class="footer">
            Agri Broker • AI-powered agricultural marketplace • Built with FastAPI + Supabase
        </div>

        <script>
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                    }
                });
            }, { threshold: 0.08 });

            document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

            function toggleChatbot() {
                const panel = document.getElementById('chatbotPanel');
                panel.classList.toggle('open');
            }

            function appendMessage(type, text, extraClass = '') {
                const messages = document.getElementById('chatMessages');
                const div = document.createElement('div');
                div.className = `chat-message ${type} ${extraClass}`;
                div.textContent = text;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
                return div;
            }

            function handleChatKey(event) {
                if (event.key === 'Enter') {
                    sendChatMessage();
                }
            }

            function sendSuggestion(text) {
                const input = document.getElementById('chatInput');
                input.value = text;
                sendChatMessage();
            }

            async function sendChatMessage() {
                const input = document.getElementById('chatInput');
                const message = input.value.trim();

                if (!message) {
                    return;
                }

                appendMessage('user', message);
                input.value = '';

                const typing = appendMessage('bot', 'Thinking...', 'typing');

                try {
                    const response = await fetch('/web/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            message: message
                        })
                    });

                    const data = await response.json();
                    typing.remove();

                    appendMessage(
                        'bot',
                        data.reply || 'I could not generate a reply. Please try again.'
                    );
                } catch (error) {
                    typing.remove();
                    appendMessage(
                        'bot',
                        'Sorry, the AI assistant is temporarily unavailable. Please try again.'
                    );
                }
            }
        </script>
    </body>
    </html>
    """

    return (
        template
        .replace("__TITLE__", escape(title))
        .replace("__BODY__", body)
        .replace("__ICON_LEAF__", icon("leaf"))
        .replace("__ICON_BRAIN__", icon("brain"))
        .replace("__ICON_SEND__", icon("send"))
    )


@router.get("/")
def web_home():
    body = f"""
    <section class="hero">
        <h1>AI Agriculture Marketplace Built for Modern Trade</h1>
        <p>
            Agri Broker connects farmers, buyers, traders, and transporters in one smart platform.
            List produce, find supply, unlock logistics, and manage agricultural trade with a clean,
            modern SaaS experience.
        </p>

        <div class="actions">
            <a class="button" href="/web/sell">{icon("store")} Sell Produce</a>
            <a class="button secondary" href="/web/buy">{icon("cart")} Buy Produce</a>
            <a class="button secondary" href="/web/transporter">{icon("truck")} Register Transporter</a>
        </div>
    </section>

    <section class="stats reveal">
        <div class="stat">
            <div class="num">AI</div>
            <div class="label">Smart extraction and matching logic</div>
        </div>
        <div class="stat">
            <div class="num">24/7</div>
            <div class="label">Always available online marketplace</div>
        </div>
        <div class="stat">
            <div class="num">Fast</div>
            <div class="label">Quick listings and buyer requests</div>
        </div>
        <div class="stat">
            <div class="num">Modern</div>
            <div class="label">Portfolio-grade SaaS presentation</div>
        </div>
    </section>

    <section class="reveal" style="margin-top: 30px;">
        <h2 class="section-title">Choose how you want to use Agri Broker</h2>
        <p class="section-subtitle">
            Whether you are selling produce, looking for stock, or transporting loads,
            the platform gives you a clean and structured digital workflow.
        </p>

        <div class="grid">
            <div class="card">
                <div class="icon-box">{icon("store")}</div>
                <h3>For Farmers & Sellers</h3>
                <p class="muted">
                    Post crops, livestock, or processed farm products with quantity,
                    pricing, and location in a simple, structured form.
                </p>
                <div style="margin-top: 18px;">
                    <a class="button" href="/web/sell">{icon("store")} Create Listing</a>
                </div>
            </div>

            <div class="card">
                <div class="icon-box">{icon("cart")}</div>
                <h3>For Buyers & Traders</h3>
                <p class="muted">
                    Submit purchase requests for produce and stock so the system can help
                    you connect with relevant nearby supply.
                </p>
                <div style="margin-top: 18px;">
                    <a class="button" href="/web/buy">{icon("cart")} Post Buy Request</a>
                </div>
            </div>

            <div class="card">
                <div class="icon-box">{icon("truck")}</div>
                <h3>For Transporters</h3>
                <p class="muted">
                    Register your vehicle and become part of the agricultural logistics network
                    to receive relevant delivery opportunities.
                </p>
                <div style="margin-top: 18px;">
                    <a class="button" href="/web/transporter">{icon("truck")} Register Vehicle</a>
                </div>
            </div>
        </div>
    </section>

    <section class="card reveal" style="margin-top: 28px;">
        <h2>Core Platform Features</h2>
        <div style="margin-top: 10px;">
            <span class="badge">{icon("brain")} AI extraction</span>
            <span class="badge">{icon("target")} Buyer-seller matching</span>
            <span class="badge">{icon("globe")} Location-aware workflows</span>
            <span class="badge">{icon("truck")} Transport pooling</span>
            <span class="badge">{icon("shield")} Trust scoring</span>
            <span class="badge">{icon("chart")} Admin dashboard</span>
            <span class="badge">{icon("bolt")} WhatsApp-ready backend</span>
            <span class="badge">{icon("globe")} Web app version</span>
        </div>

        <p class="muted" style="margin-top: 18px;">
            This web version showcases the Agri Broker concept as a polished, SaaS-style product
            while keeping the backend ready for messaging, data capture, matching, and logistics automation.
        </p>
    </section>
    """

    return HTMLResponse(page_layout("Agri Broker Web App", body))


@router.get("/sell")
def sell_form():
    body = f"""
    <section class="card reveal">
        <h2>Sell Produce</h2>
        <p class="muted">
            Enter the details of what you are selling.
        </p>

        <form method="post" action="/web/sell">
            <div class="field-row">
                <div>
                    <label>Your Name</label>
                    <input name="name" placeholder="Example: Tawanda" required />
                </div>
                <div>
                    <label>WhatsApp Phone</label>
                    <input name="phone" placeholder="26377xxxxxxx" required />
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Commodity</label>
                    <input name="commodity" placeholder="Tomatoes, maize, goats, beef..." required />
                </div>
                <div>
                    <label>Location</label>
                    <input name="location" placeholder="Chegutu, Kadoma, Harare..." required />
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Quantity</label>
                    <input name="quantity" type="number" step="0.01" placeholder="20" required />
                </div>
                <div>
                    <label>Unit</label>
                    <select name="unit">
                        <option value="kg">kg</option>
                        <option value="bags">bags</option>
                        <option value="boxes">boxes</option>
                        <option value="crates">crates</option>
                        <option value="">animals / each</option>
                    </select>
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Total Price</label>
                    <input name="price" type="number" step="0.01" placeholder="Optional" />
                </div>
                <div>
                    <label>Currency</label>
                    <select name="currency">
                        <option value="USD">USD</option>
                        <option value="ZIG">ZIG</option>
                        <option value="ZAR">ZAR</option>
                    </select>
                </div>
            </div>

            <label>Transport Option</label>
            <select name="delivery_option">
                <option value="unknown">Not sure</option>
                <option value="can_deliver">I can deliver</option>
                <option value="buyer_collects">Buyer collects</option>
                <option value="needs_transport">Need transport help</option>
            </select>

            <label>Extra Notes</label>
            <textarea name="notes" placeholder="Example: fresh stock, ready today, can deliver nearby"></textarea>

            <button class="button" type="submit">{icon("store")} Submit Sell Listing</button>
        </form>
    </section>
    """

    return HTMLResponse(page_layout("Sell Produce - Agri Broker", body))


@router.post("/sell")
def submit_sell(
    name: str = Form(...),
    phone: str = Form(...),
    commodity: str = Form(...),
    location: str = Form(...),
    quantity: float = Form(...),
    unit: str = Form(""),
    price: str = Form(""),
    currency: str = Form("USD"),
    delivery_option: str = Form("unknown"),
    notes: str = Form(""),
):
    
    try:
        name = clean_text(name, "Name", 80)
        phone = clean_phone(phone)
        commodity = clean_text(commodity, "Commodity", 80)
        location = clean_text(location, "Location", 120)
        notes = clean_text(notes, "Notes", 500, required=False)
        quantity = validate_positive_number(quantity, "Quantity")
        unit = validate_choice(unit, ALLOWED_UNITS, "Unit")
        currency = validate_choice(currency, ALLOWED_CURRENCIES, "Currency")
        delivery_option = validate_choice(delivery_option, ALLOWED_SELL_DELIVERY_OPTIONS, "Transport option")
        price_value = validate_optional_price(price)
    except ValueError as e:
        return validation_error(str(e))    
    normalized_location = normalize_location_name(location)

    price_per_unit = None

    if price_value is not None and quantity > 0:
        price_per_unit = price_value / quantity

    save_listing({
        "type": "listing",
        "intent": "sell",
        "commodity": commodity.strip().lower(),
        "quantity": quantity,
        "unit": unit,
        "raw_quantity_text": f"{quantity} {unit}".strip(),
        "location": normalized_location or location,
        "confidence": 1,
        "raw": notes,
        "seller_phone": phone,
        "price": price_value,
        "currency": currency,
        "price_per_unit": price_per_unit,
        "delivery_option": delivery_option,
        "transport_needed": delivery_option == "needs_transport",
        "transport_note": notes,
        "location_source": "web_form",
    })

    try:
        supabase.table("user_profiles").upsert({
            "phone": phone,
            "name": name,
            "city": normalized_location or location,
            "role": "seller",
        }, on_conflict="phone").execute()
    except Exception as e:
        print("Profile web upsert error:", e)

    body = f"""
    <section class="success">
        <h2>Listing submitted successfully</h2>
        <p>Your listing has been saved and is ready for future matching workflows.</p>
    </section>

    <section class="card reveal">
        <h3>Listing Summary</h3>
        <p><strong>Seller:</strong> {escape(name)}</p>
        <p><strong>Commodity:</strong> {escape(commodity)}</p>
        <p><strong>Quantity:</strong> {quantity} {escape(unit)}</p>
        <p><strong>Location:</strong> {escape(normalized_location or location)}</p>
        <p><strong>Price:</strong> {escape(currency)} {price_value if price_value else "Not specified"}</p>
        <p><strong>Status:</strong> Active</p>

        <div class="actions">
            <a class="button" href="/web/sell">{icon("store")} Submit Another</a>
            <a class="button secondary" href="/web">{icon("leaf")} Back Home</a>
        </div>
    </section>
    """

    return HTMLResponse(page_layout("Listing Submitted", body))


@router.get("/buy")
def buy_form():
    body = f"""
    <section class="card reveal">
        <h2>Buy Produce</h2>
        <p class="muted">
            Enter what you want to buy and the quantity needed.
        </p>

        <form method="post" action="/web/buy">
            <div class="field-row">
                <div>
                    <label>Your Name</label>
                    <input name="name" placeholder="Example: Rudo" required />
                </div>
                <div>
                    <label>WhatsApp Phone</label>
                    <input name="phone" placeholder="26377xxxxxxx" required />
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Commodity Needed</label>
                    <input name="commodity" placeholder="Maize, tomatoes, goats, beef..." required />
                </div>
                <div>
                    <label>Your Location</label>
                    <input name="location" placeholder="Harare, Kadoma, Bulawayo..." required />
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Quantity Needed</label>
                    <input name="quantity" type="number" step="0.01" placeholder="10" required />
                </div>
                <div>
                    <label>Unit</label>
                    <select name="unit">
                        <option value="kg">kg</option>
                        <option value="bags">bags</option>
                        <option value="boxes">boxes</option>
                        <option value="crates">crates</option>
                        <option value="">animals / each</option>
                    </select>
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Budget</label>
                    <input name="price" type="number" step="0.01" placeholder="Optional" />
                </div>
                <div>
                    <label>Currency</label>
                    <select name="currency">
                        <option value="USD">USD</option>
                        <option value="ZIG">ZIG</option>
                        <option value="ZAR">ZAR</option>
                    </select>
                </div>
            </div>

            <label>Transport Option</label>
            <select name="delivery_option">
                <option value="unknown">Not sure</option>
                <option value="will_collect">I will collect</option>
                <option value="needs_transport">Need transport help</option>
            </select>

            <label>Extra Notes</label>
            <textarea name="notes" placeholder="Example: need delivery to Mbare, looking for fresh stock"></textarea>

            <button class="button" type="submit">{icon("cart")} Submit Buy Request</button>
        </form>
    </section>
    """

    return HTMLResponse(page_layout("Buy Produce - Agri Broker", body))


@router.post("/buy")
def submit_buy(
    name: str = Form(...),
    phone: str = Form(...),
    commodity: str = Form(...),
    location: str = Form(...),
    quantity: float = Form(...),
    unit: str = Form(""),
    price: str = Form(""),
    currency: str = Form("USD"),
    delivery_option: str = Form("unknown"),
    notes: str = Form(""),
):
    try:
        name = clean_text(name, "Name", 80)
        phone = clean_phone(phone)
        commodity = clean_text(commodity, "Commodity", 80)
        location = clean_text(location, "Location", 120)
        notes = clean_text(notes, "Notes", 500, required=False)
        quantity = validate_positive_number(quantity, "Quantity")
        unit = validate_choice(unit, ALLOWED_UNITS, "Unit")
        currency = validate_choice(currency, ALLOWED_CURRENCIES, "Currency")
        delivery_option = validate_choice(delivery_option, ALLOWED_BUY_DELIVERY_OPTIONS, "Transport option")
        price_value = validate_optional_price(price)
    except ValueError as e:
        return validation_error(str(e))    
    normalized_location = normalize_location_name(location)

    price_per_unit = None

    if price_value is not None and quantity > 0:
        price_per_unit = price_value / quantity
    save_listing({
        "type": "listing",
        "intent": "buy",
        "commodity": commodity.strip().lower(),
        "quantity": quantity,
        "unit": unit,
        "raw_quantity_text": f"{quantity} {unit}".strip(),
        "location": normalized_location or location,
        "confidence": 1,
        "raw": notes,
        "seller_phone": phone,
        "price": price_value,
        "currency": currency,
        "price_per_unit": price_per_unit,
        "delivery_option": delivery_option,
        "transport_needed": delivery_option == "needs_transport",
        "transport_note": notes,
        "location_source": "web_form",
    })

    try:
        supabase.table("user_profiles").upsert({
            "phone": phone,
            "name": name,
            "city": normalized_location or location,
            "role": "buyer",
        }, on_conflict="phone").execute()
    except Exception as e:
        print("Profile web upsert error:", e)

    body = f"""
    <section class="success">
        <h2>Buy request submitted successfully</h2>
        <p>Your request has been saved and is ready for future matching workflows.</p>
    </section>

    <section class="card reveal">
        <h3>Request Summary</h3>
        <p><strong>Buyer:</strong> {escape(name)}</p>
        <p><strong>Commodity:</strong> {escape(commodity)}</p>
        <p><strong>Quantity:</strong> {quantity} {escape(unit)}</p>
        <p><strong>Location:</strong> {escape(normalized_location or location)}</p>
        <p><strong>Budget:</strong> {escape(currency)} {price_value if price_value else "Not specified"}</p>
        <p><strong>Status:</strong> Active</p>

        <div class="actions">
            <a class="button" href="/web/buy">{icon("cart")} Submit Another</a>
            <a class="button secondary" href="/web">{icon("leaf")} Back Home</a>
        </div>
    </section>
    """

    return HTMLResponse(page_layout("Buy Request Submitted", body))


@router.get("/transporter")
def transporter_form():
    body = f"""
    <section class="card reveal">
        <h2>Register as Transporter</h2>
        <p class="muted">
            Register your vehicle to receive agriculture transport opportunities.
            Your profile will still need admin verification before jobs are assigned.
        </p>

        <form method="post" action="/web/transporter">
            <div class="field-row">
                <div>
                    <label>Name / Company</label>
                    <input name="name" placeholder="Example: Tinashe Transport" required />
                </div>
                <div>
                    <label>WhatsApp Phone</label>
                    <input name="phone" placeholder="26377xxxxxxx" required />
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Base Location</label>
                    <input name="base_location" placeholder="Harare, Chegutu, Kadoma..." required />
                </div>
                <div>
                    <label>Vehicle Type</label>
                    <input name="vehicle_type" placeholder="1 tonne truck, pickup, lorry..." required />
                </div>
            </div>

            <div class="field-row">
                <div>
                    <label>Capacity</label>
                    <input name="vehicle_capacity" type="number" step="0.01" placeholder="1000" required />
                </div>
                <div>
                    <label>Capacity Unit</label>
                    <select name="capacity_unit">
                        <option value="kg">kg</option>
                        <option value="tonnes">tonnes</option>
                        <option value="boxes">boxes</option>
                        <option value="bags">bags</option>
                    </select>
                </div>
            </div>

            <button class="button" type="submit">{icon("truck")} Register Transporter</button>
        </form>
    </section>
    """

    return HTMLResponse(page_layout("Transporter Registration - Agri Broker", body))


@router.post("/transporter")
def submit_transporter(
    name: str = Form(...),
    phone: str = Form(...),
    base_location: str = Form(...),
    vehicle_type: str = Form(...),
    vehicle_capacity: float = Form(...),
    capacity_unit: str = Form("kg"),
):
    try:
        name = clean_text(name, "Name / Company", 100)
        phone = clean_phone(phone)
        base_location = clean_text(base_location, "Base location", 120)
        vehicle_type = clean_text(vehicle_type, "Vehicle type", 100)
        vehicle_capacity = validate_positive_number(vehicle_capacity, "Vehicle capacity")
        capacity_unit = validate_choice(capacity_unit, ALLOWED_CAPACITY_UNITS, "Capacity unit")
    except ValueError as e:
        return validation_error(str(e))    
    normalized_location = normalize_location_name(base_location)

    register_or_update_transporter(
        phone=phone,
        name=name,
        base_location=normalized_location or base_location,
        vehicle_type=vehicle_type,
        vehicle_capacity=vehicle_capacity,
        capacity_unit=capacity_unit,
        is_verified=False,
    )

    body = f"""
    <section class="success">
        <h2>Transporter registration submitted successfully</h2>
        <p>Your transporter profile is now pending admin verification.</p>
    </section>

    <section class="card reveal">
        <h3>Transporter Summary</h3>
        <p><strong>Name:</strong> {escape(name)}</p>
        <p><strong>Phone:</strong> {escape(phone)}</p>
        <p><strong>Base:</strong> {escape(normalized_location or base_location)}</p>
        <p><strong>Vehicle:</strong> {escape(vehicle_type)}</p>
        <p><strong>Capacity:</strong> {vehicle_capacity} {escape(capacity_unit)}</p>
        <p><strong>Status:</strong> Pending verification</p>

        <div class="actions">
            <a class="button" href="/web/transporter">{icon("truck")} Register Another</a>
            <a class="button secondary" href="/web">{icon("leaf")} Back Home</a>
        </div>
    </section>
    """

    return HTMLResponse(page_layout("Transporter Submitted", body))


@router.get("/portfolio")
def old_portfolio_redirect():
    return RedirectResponse(url="/web/case-study", status_code=302)


@router.get("/case-study")
def case_study_page():
    body = f"""
    <section class="hero">
        <h1>Case Study: Agri Broker</h1>
        <p>
            A full-stack AI-powered agriculture marketplace built with FastAPI,
            Supabase, matching workflows, admin dashboards, and a polished
            web experience designed for product demos and job applications.
        </p>

        <div class="actions">
            <a class="button" href="/web">{icon("globe")} View Product Demo</a>
            <a class="button secondary" href="/web/sell">{icon("store")} Try Seller Flow</a>
            <a class="button secondary" href="/web/buy">{icon("cart")} Try Buyer Flow</a>
        </div>
    </section>

    <section class="grid-2 reveal" style="margin-top: 28px;">
        <div class="card">
            <div class="icon-box">{icon("target")}</div>
            <h2>Problem</h2>
            <p class="muted">
                Farmers, buyers, and transporters struggle with market access,
                trust, logistics coordination, and structured digital workflows.
                Most activity happens informally through calls and WhatsApp messages.
            </p>
        </div>

        <div class="card">
            <div class="icon-box">{icon("bolt")}</div>
            <h2>Solution</h2>
            <p class="muted">
                Agri Broker digitizes buyer-seller workflows with listing capture,
                request capture, transporter onboarding, AI assistance, matching logic,
                and operational dashboards.
            </p>
        </div>
    </section>

    <section class="card reveal" style="margin-top: 28px;">
        <h2>Key Features Built</h2>
        <div style="margin-top: 10px;">
            <span class="badge">{icon("bolt")} FastAPI backend</span>
            <span class="badge">{icon("globe")} Supabase database</span>
            <span class="badge">{icon("brain")} Gemini AI assistant</span>
            <span class="badge">{icon("target")} Smart matching</span>
            <span class="badge">{icon("truck")} Transporter onboarding</span>
            <span class="badge">{icon("shield")} Trust and reporting</span>
            <span class="badge">{icon("chart")} Admin dashboard</span>
            <span class="badge">{icon("globe")} Responsive web app</span>
            <span class="badge">{icon("bolt")} Render deployment</span>
        </div>
    </section>

    <section class="grid-2 reveal" style="margin-top: 28px;">
        <div class="card">
            <h2>Tech Stack</h2>
            <p><strong>Backend:</strong> FastAPI, Python</p>
            <p><strong>Database:</strong> Supabase / PostgreSQL</p>
            <p><strong>AI:</strong> Gemini-powered assistant and extraction logic</p>
            <p><strong>Frontend:</strong> Server-rendered interactive SaaS-style UI</p>
            <p><strong>Deployment:</strong> Render</p>
        </div>

        <div class="card">
            <h2>Business Value</h2>
            <p class="muted">
                The system is designed to help farmers find buyers, buyers find stock,
                and transporters find delivery opportunities while laying the foundation
                for monetization through premium visibility, lead access, and verified logistics.
            </p>
        </div>
    </section>

    <section class="card reveal" style="margin-top: 28px;">
        <h2>Portfolio Pitch</h2>
        <p class="muted">
            I built Agri Broker as a production-style full-stack SaaS platform. It includes
            database design, API development, web application UI, AI-powered workflows,
            structured forms, dashboarding, and deployment architecture for a real-world
            agriculture marketplace.
        </p>
    </section>
    """

    return HTMLResponse(page_layout("Agri Broker Case Study", body))