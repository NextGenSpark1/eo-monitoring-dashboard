# ================================================================================
# src/telegram_helper.py — Telegram Alert System
# ================================================================================
# Developer  : Habiba Hassan (AI Analytics & Visualization)
# Description: Telegram bot integration — message sending, alert formatting,
#              subscriber management, and test alert utilities.
# ================================================================================

import os
import requests
from datetime import datetime


# CONFIG

def get_bot_token():
    """Read Telegram bot token from Streamlit secrets or environment variable."""
    try:
        import streamlit as st
        return st.secrets["telegram"]["bot_token"]
    except Exception:
        pass
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


# CORE SENDER

def send_telegram_message(chat_id, message):
    """
    Send a single Telegram message to one chat ID.
    Returns (ok: bool, info: str).
    """
    token = get_bot_token()
    if not token:
        return False, "Bot token not configured."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "Sent"
        return False, response.json().get("description", "Unknown error")
    except Exception as exception:
        return False, str(exception)


def broadcast_to_subscribers(message):
    """
    Send the same message to every subscriber stored in Supabase.
    Returns (sent_count, failed_count).
    """
    from src.database import get_all_subscribers

    subscribers = get_all_subscribers()
    sent = 0
    failed = 0
    for chat_id in subscribers:
        ok, _ = send_telegram_message(chat_id, message)
        if ok:
            sent += 1
        else:
            failed += 1
    return sent, failed


# MESSAGE BUILDERS

def build_alert_message(zone_name, index_value, status, value_col, module_name, event_label=None):
    """Build the standard alert message used by both dashboard and pipeline."""
    now = datetime.now().strftime("%d %b %Y, %H:%M")
    index_label = "NDTI" if value_col == "turbidity" else "NDVI"
    status_emoji = "🔴" if status == "critical" else "🟡"
    status_label = "CRITICAL" if status == "critical" else "WARNING"

    insight_line = f"\n<b>Insight:</b> {event_label}\n" if event_label else ""

    return (
        f"<b>{status_emoji} {status_label} — {module_name} Zone Alert</b>\n\n"
        f"<b>Zone:</b> {zone_name}\n"
        f"<b>Time:</b> {now}\n"
        f"<b>{index_label}:</b> {index_value}\n"
        f"<b>Status:</b> {status_label}\n"
        f"{insight_line}\n"
        f"Please open the dashboard to review the latest readings and take action if needed.\n\n"
        f"<i>TNB Siltation Monitor — EO Dashboard</i>"
    )


def build_test_message():
    """Demo test message shown when the user clicks the Test Alert button."""
    return build_alert_message(
        zone_name="Empangan Sultan Abu Bakar",
        index_value="0.142",
        status="critical",
        value_col="turbidity",
        module_name="Hydro",
        event_label="Simulated event — system check only",
    )


# CONVENIENCE WRAPPERS

def send_test_alert(chat_id):
    """Send a test alert to one chat ID (used by the dashboard button)."""
    return send_telegram_message(chat_id, build_test_message())


def send_subscription_welcome(chat_id):
    """Send the welcome message after a successful subscription."""
    message = (
        "You are now subscribed to TNB Siltation Monitor alerts.\n\n"
        "You will receive notifications when any zone exceeds the configured thresholds.\n\n"
        "TNB Siltation Monitor — EO Dashboard"
    )
    return send_telegram_message(chat_id, message)
