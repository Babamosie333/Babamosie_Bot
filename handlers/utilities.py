# ============================================================
#  handlers/utilities.py
#  /time, /weather, /news commands
# ============================================================

import datetime
import requests
import os, json
from telegram import Update
from telegram.ext import ContextTypes

PREFS_FILE = "user_prefs.json"

def _get_user_pref(user_id: str, key: str, default=None):
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE) as f:
            prefs = json.load(f)
        return prefs.get(user_id, {}).get(key, default)
    return default


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return current date and time in a nice format."""
    now = datetime.datetime.now()
    day   = now.strftime("%A")                     # e.g. "Friday"
    date  = now.strftime("%d %B %Y")              # e.g. "13 June 2025"
    clock = now.strftime("%I:%M:%S %p")           # e.g. "10:30:45 AM"

    text = (
        f"🕐 *Current Time*\n\n"
        f"📅 {day}, {date}\n"
        f"⏰ {clock} (IST)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch weather — uses saved city from /setcity if no arg given."""
    user_id    = str(update.effective_user.id)
    saved_city = _get_user_pref(user_id, "city", None)

    if not context.args:
        if saved_city:
            city = saved_city
        else:
            await update.message.reply_text(
                "Please provide a city name.\n"
                "Example: `/weather Varanasi`\n\n"
                "💡 Tip: Use `/setcity Varanasi` to save your city so you\n"
                "never need to type it again!",
                parse_mode="Markdown"
            )
            return
    else:
        city = " ".join(context.args)

    using_saved = (not context.args and saved_city)

    try:
        # format=j1 returns full JSON with temperature, humidity, conditions
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url, timeout=6)
        data = resp.json()

        # Extract the fields we need from the nested JSON
        current   = data["current_condition"][0]
        temp_c    = current["temp_C"]
        feels     = current["FeelsLikeC"]
        humidity  = current["humidity"]
        desc      = current["weatherDesc"][0]["value"]
        wind_kmph = current["windspeedKmph"]

        saved_note = f"\n_📍 Using your saved city — change with /setcity_" if using_saved else ""

        text = (
            f"🌤 *Weather in {city.title()}*\n\n"
            f"🌡 Temperature: *{temp_c}°C* (feels like {feels}°C)\n"
            f"🌥 Condition: {desc}\n"
            f"💧 Humidity: {humidity}%\n"
            f"💨 Wind: {wind_kmph} km/h"
            f"{saved_note}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text(
            f"❌ Couldn't get weather for *{city}*. Check the city name and try again.",
            parse_mode="Markdown"
        )


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch top 5 news headlines using GNews free API (no key needed for basic use)."""
    await update.message.reply_text("📰 Fetching latest headlines…")

    try:
        # Using NewsData.io free tier OR a simple RSS-based approach via rss2json
        url = "https://rss2json.com/api.json?rss_url=https://feeds.bbci.co.uk/news/world/rss.xml"
        resp = requests.get(url, timeout=8)
        data = resp.json()

        items = data.get("items", [])[:5]   # Take only the top 5 articles

        if not items:
            await update.message.reply_text("No headlines found right now. Try again later.")
            return

        lines = ["📰 *Top 5 World Headlines*\n"]
        for i, item in enumerate(items, 1):
            title = item.get("title", "No title")
            link  = item.get("link",  "#")
            lines.append(f"{i}. [{title}]({link})")

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            disable_web_page_preview=True   # Don't show link previews (keeps it clean)
        )

    except Exception:
        await update.message.reply_text("❌ News service unavailable right now. Try again later.")
