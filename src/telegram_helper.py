

import requests
import os
from datetime import datetime



# TELEGRAM CONFIG

def get_telegram_config():
    """
    Get Telegram bot token and chat ID.
    Tries Streamlit secrets first, then environment variables.
    """
    try:
        import streamlit as st
        return (
            st.secrets["telegram"]["bot_token"],
            st.secrets["telegram"]["chat_id"]
        )
    except Exception:
        pass

    # Fallback to environment variables
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id   = os.environ.get("TELEGRAM_CHAT_ID")

    if bot_token and chat_id:
        return bot_token, chat_id

    return None, None



# SEND MESSAGE

def send_telegram_message(message):
    """
    Send a message via Telegram bot.

    Returns:
        bool: True if sent successfully, False otherwise
    """
    bot_token, chat_id = get_telegram_config()

    if not bot_token or not chat_id:
        print("⚠️  Telegram not configured. Add bot_token and chat_id to secrets.")
        return False

    url  = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id":    chat_id,
        "text":       message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram message sent successfully")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code} — {response.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram failed: {e}")
        return False


# ALERT MESSAGES

def send_critical_alert(zone, ndti_value, date=None):
    """
    Send a critical siltation alert to Telegram.
    Called by alert_system.py and the dashboard test button.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = (
        f"🚨 <b>CRITICAL SILTATION ALERT</b>\n\n"
        f"📍 <b>Zone:</b> {zone}\n"
        f"📅 <b>Date:</b> {date}\n"
        f"💧 <b>NDTI:</b> {ndti_value:.4f}\n"
        f"⚠️ <b>Status:</b> CRITICAL — High Turbidity\n\n"
        f"🏗️ <b>Recommended Action:</b>\n"
        f"Deploy dredging barge to this zone immediately.\n"
        f"Estimated silt accumulation is above safe threshold.\n\n"
        f"🤖 <i>TNB Siltation Monitor — Automated Alert</i>"
    )
    return send_telegram_message(message)


def send_warning_alert(zone, ndti_value, date=None):
    """Send a warning level alert."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = (
        f"⚠️ <b>SILTATION WARNING</b>\n\n"
        f"📍 <b>Zone:</b> {zone}\n"
        f"📅 <b>Date:</b> {date}\n"
        f"💧 <b>NDTI:</b> {ndti_value:.4f}\n"
        f"⚠️ <b>Status:</b> WARNING — Moderate Turbidity\n\n"
        f"👀 <b>Recommended Action:</b>\n"
        f"Monitor this zone closely over the next 7 days.\n"
        f"Schedule dredging if level rises further.\n\n"
        f"🤖 <i>TNB Siltation Monitor — Automated Alert</i>"
    )
    return send_telegram_message(message)


def send_test_alert(zone="Empangan Sultan Abu Bakar"):
    """
    Demo test alert — triggered by Habiba's dashboard button.
    Sends a realistic looking critical alert to demonstrate the system.
    """
    message = (
        f"🚨 <b>TEST ALERT — TNB Siltation Monitor</b>\n\n"
        f"📍 <b>Zone:</b> {zone}\n"
        f"📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"💧 <b>NDTI:</b> 0.1420 (Simulated)\n"
        f"⚠️ <b>Status:</b> CRITICAL — High Turbidity\n\n"
        f"🏗️ <b>Recommended Action:</b>\n"
        f"Deploy dredging barge immediately.\n"
        f"Estimated silt accumulation exceeds safe threshold.\n\n"
        f"✅ <i>This is a test message. System is working correctly.</i>\n"
        f"🤖 <i>TNB Siltation Monitor — Demo Mode</i>"
    )
    success = send_telegram_message(message)

    if success:
        return True, "✅ Test alert sent! Check your Telegram."
    else:
        return False, "❌ Failed to send. Check Telegram configuration in secrets."



# SETUP INSTRUCTIONS (printed when run directly)


if __name__ == "__main__":
    print("=" * 55)
    print("  Telegram Setup Guide")
    print("=" * 55)
    print("do it yourself")
    print("Testing connection...")
    success, msg = send_test_alert()
    print(msg)
