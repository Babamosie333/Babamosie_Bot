# ============================================================
#  handlers/briefing.py
#  Daily Morning Briefing — auto-sent to all users at 8:00 AM
#
#  Sends: greeting + weather (Kanpur default) + quote + news
#
#  Uses APScheduler to run background cron jobs.
#  Install: pip install apscheduler
# ============================================================

import json
import os
import random
import requests
from datetime import datetime
from telegram.ext import Application

USERS_FILE = "users_db.json"

# Default city for weather in briefing (change as needed)
DEFAULT_CITY = "Kanpur"

MORNING_QUOTES = [
    "The secret of getting ahead is getting started. 🚀",
    "Code is like humor — when you have to explain it, it's bad. 😄",
    "Every day is a chance to learn something new. 📚",
    "Push yourself, because no one else is going to do it for you. 💪",
    "Great things never came from comfort zones. 🌟",
    "First, solve the problem. Then, write the code. 💡",
    "Dream it. Wish it. Do it. ✨",
    "Stay hungry, stay foolish. — Steve Jobs 🍎",
    "Your only limit is your mind. 🧠",
    "Make today so awesome that yesterday gets jealous. 😎",
]


def get_weather_brief(city: str) -> str:
    """Fetch a short weather summary for the briefing."""
    try:
        url  = f"https://wttr.in/{city}?format=j1"
        data = requests.get(url, timeout=5).json()
        c    = data["current_condition"][0]
        temp = c["temp_C"]
        desc = c["weatherDesc"][0]["value"]
        return f"🌤 *Weather in {city}:* {temp}°C, {desc}"
    except Exception:
        return f"🌤 Weather unavailable today."


def get_news_brief() -> str:
    """Fetch top 3 headlines for the briefing."""
    try:
        url  = "https://rss2json.com/api.json?rss_url=https://feeds.bbci.co.uk/news/world/rss.xml"
        data = requests.get(url, timeout=6).json()
        items = data.get("items", [])[:3]
        if not items:
            return "📰 No news available."
        lines = ["📰 *Top Headlines:*"]
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item.get('title', '')}")
        return "\n".join(lines)
    except Exception:
        return "📰 News unavailable today."


async def send_daily_briefing(app: Application):
    """
    Called automatically at 8:00 AM every day by APScheduler.
    Sends personalized morning briefing to all registered users.
    """
    if not os.path.exists(USERS_FILE):
        return

    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    if not users:
        return

    now     = datetime.now()
    date    = now.strftime("%A, %d %B %Y")
    quote   = random.choice(MORNING_QUOTES)
    weather = get_weather_brief(DEFAULT_CITY)
    news    = get_news_brief()

    for uid, data in users.items():
        name = data.get("first_name", "there")
        try:
            message = (
                f"☀️ *Good Morning, {name}!*\n"
                f"📅 {date}\n\n"
                f"{weather}\n\n"
                f"💬 *Quote of the Day:*\n_{quote}_\n\n"
                f"{news}\n\n"
                f"━━━━━━━━━━━━\n"
                f"Have a productive day! 🚀\n"
                f"Type /help to see what I can do."
            )
            await app.bot.send_message(
                chat_id=int(uid),
                text=message,
                parse_mode="Markdown"
            )
        except Exception:
            pass   # User may have blocked the bot — skip silently


def setup_scheduler(app: Application):
    """
    Registers the scheduler to start AFTER the bot is fully running.
    Uses post_init hook so the asyncio event loop is already active.
    This fixes: RuntimeError: no running event loop
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        # post_init is called by python-telegram-bot AFTER the event loop starts
        # This is the correct place to start AsyncIOScheduler
        async def post_init(application: Application):
            from handlers.automation import check_birthdays, check_price_alerts
            scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
            # Daily morning briefing at 8:00 AM IST
            scheduler.add_job(
                send_daily_briefing,
                trigger="cron",
                hour=8, minute=0,
                args=[application]
            )
            # Birthday check every morning at 8:00 AM IST
            scheduler.add_job(
                check_birthdays,
                trigger="cron",
                hour=8, minute=1,
                args=[application]
            )
            # Price alert check every 30 minutes
            scheduler.add_job(
                check_price_alerts,
                trigger="interval",
                minutes=30,
                args=[application]
            )
            scheduler.start()
            print("✅ Scheduler started — briefing 8AM · birthdays 8:01AM · price alerts every 30min")

        # Attach the hook to the app
        app.post_init = post_init
        print("📅 Daily briefing scheduled (will activate after bot starts)")

    except ImportError:
        print("⚠️  APScheduler not installed. Run: pip install apscheduler")
        return None


# ── Manual trigger for testing ────────────────────────────
async def test_briefing_command(update, context):
    """
    /testbrief — Send yourself the morning briefing right now (admin only).
    Use this to test the briefing before waiting until 8 AM!
    """
    from handlers.admin import is_admin
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    await update.message.reply_text("📨 Sending test briefing to all users...")
    await send_daily_briefing(context.application)
    await update.message.reply_text("✅ Test briefing sent!")
