# ============================================================
#  handlers/menu.py
#  /menu — Interactive button menu
#  /ping — Bot health check
#  /feedback <message> — Send feedback to admin
# ============================================================

import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

ADMIN_ID      = int(os.environ.get("ADMIN_ID", "0"))
FEEDBACK_FILE = "feedback.json"

# ── Menu pages ────────────────────────────────────────────

MENU_PAGES = {
    "main": {
        "title": "🤖 *Vikram's Bot v8.0 — Main Menu*\n\nChoose a category:",
        "buttons": [
            [("🧠 AI & Chat",       "menu|ai"),      ("🎮 Games & Fun",    "menu|games")],
            [("📊 Finance",          "menu|finance"),  ("🎬 Media",          "menu|media")],
            [("📚 Student Tools",    "menu|student"),  ("⚡ Productivity",   "menu|productivity")],
            [("🔔 Automation",       "menu|automation"),("🛠 Utilities",     "menu|utilities")],
            [("🔐 Security",         "menu|security"), ("👥 Group Admin",    "menu|group")],
            [("⚙️ Personalize",      "menu|personal"), ("📊 Stats & Admin",  "menu|admin")],
        ]
    },
    "ai": {
        "title": "🧠 *AI & Chat Commands*",
        "buttons": [
            [("🤖 /ai",         "cmd|ai"),        ("💬 /ask",        "cmd|ask")],
            [("🎨 /imagine",    "cmd|imagine"),   ("🧠 /explain",    "cmd|explain")],
            [("💻 /code",       "cmd|code"),      ("📝 /quiz",       "cmd|quiz")],
            [("✍️ /rewrite",   "cmd|rewrite"),   ("📋 /grammar",    "cmd|grammar")],
            [("🔗 /summarizeurl","cmd|summarizeurl"),("🧠 /memory",  "cmd|memory")],
            [("🎭 /persona",    "cmd|persona"),   ("🔥 /roast",      "cmd|roast")],
            [("⚖️ /debate",    "cmd|debate"),    ("📝 /summarize",  "cmd|summarize")],
            [("◀️ Back",        "menu|main")],
        ]
    },
    "games": {
        "title": "🎮 *Games & Fun Commands*",
        "buttons": [
            [("🎯 /hangman",    "cmd|hangman"),   ("🎲 /trivia",     "cmd|trivia")],
            [("✂️ /rps",       "cmd|rps"),       ("🎱 /8ball",      "cmd|8ball")],
            [("🤔 /wouldyourather","cmd|wouldyourather"),("😈 /dare","cmd|dare")],
            [("💘 /ship",       "cmd|ship"),      ("📖 /story",      "cmd|story")],
            [("🧮 /mathquiz",   "cmd|mathquiz"),  ("⌨️ /typetest",  "cmd|typetest")],
            [("💝 /compliment", "cmd|compliment"),("💪 /motivate",   "cmd|motivate")],
            [("◀️ Back",        "menu|main")],
        ]
    },
    "finance": {
        "title": "📊 *Finance Commands*",
        "buttons": [
            [("💰 /crypto",     "cmd|crypto"),    ("💱 /currency",   "cmd|currency")],
            [("📈 /stock",      "cmd|stock"),     ("🔔 /pricealert", "cmd|pricealert")],
            [("🏦 /emi",        "cmd|emi"),       ("⚖️ /bmi",       "cmd|bmi")],
            [("🎓 /gpa",        "cmd|gpa"),       ("◀️ Back",        "menu|main")],
        ]
    },
    "media": {
        "title": "🎬 *Media Commands*",
        "buttons": [
            [("😂 /meme",       "cmd|meme"),      ("🎬 /movie",      "cmd|movie")],
            [("🎌 /anime",      "cmd|anime"),     ("📺 /youtube",    "cmd|youtube")],
            [("🎵 /spotify",    "cmd|spotify"),   ("◀️ Back",        "menu|main")],
        ]
    },
    "student": {
        "title": "📚 *Student Tools Commands*",
        "buttons": [
            [("🗂 /flashcard",  "cmd|flashcard"), ("📝 /mcq",        "cmd|mcq")],
            [("✍️ /essay",     "cmd|essay"),     ("📐 /formula",    "cmd|formula")],
            [("📖 /dictionary", "cmd|dictionary"),("💡 /tip",        "cmd|tip")],
            [("📚 /define",     "cmd|define"),    ("🌟 /word",       "cmd|word")],
            [("🎓 /syllabus",   "cmd|syllabus"),  ("📋 /pyq",        "cmd|pyq")],
            [("📅 /studyplan",  "cmd|studyplan"), ("🤔 /doubt",      "cmd|doubt")],
            [("◀️ Back",        "menu|main")],
        ]
    },
    "productivity": {
        "title": "⚡ *Productivity Commands*",
        "buttons": [
            [("✅ /todo",       "cmd|todo"),      ("🧮 /calc",       "cmd|calc")],
            [("⏳ /countdown",  "cmd|countdown"), ("🍅 /pomodoro",   "cmd|pomodoro")],
            [("⏰ /remind",     "cmd|remind"),    ("⏱ /typetest",   "cmd|typetest")],
            [("🎂 /agedays",    "cmd|agedays"),   ("◀️ Back",        "menu|main")],
        ]
    },
    "automation": {
        "title": "🔔 *Automation Commands*",
        "buttons": [
            [("📰 /subscribe",  "cmd|subscribe"), ("🔕 /unsubscribe","cmd|unsubscribe")],
            [("💰 /pricealert", "cmd|pricealert"),("🎂 /birthday",   "cmd|birthday")],
            [("🏃 /habit",      "cmd|habit"),     ("📔 /journal",    "cmd|journal")],
            [("◀️ Back",        "menu|main")],
        ]
    },
    "utilities": {
        "title": "🛠 *Utility Commands*",
        "buttons": [
            [("🌤 /weather",    "cmd|weather"),   ("⛅ /forecast",   "cmd|forecast")],
            [("📰 /news",       "cmd|news"),      ("📰 /topicnews",  "cmd|topicnews")],
            [("🕐 /time",       "cmd|time"),      ("🌐 /timezone",   "cmd|timezone")],
            [("🌐 /translate",  "cmd|translate"), ("🔮 /horoscope",  "cmd|horoscope")],
            [("🔗 /shorten",    "cmd|shorten"),   ("📷 /qr",         "cmd|qr")],
            [("🔑 /password",   "cmd|password"),  ("🎵 /lyrics",     "cmd|lyrics")],
            [("😄 /joke",       "cmd|joke"),      ("💬 /quote",      "cmd|quote")],
            [("🤯 /fact",       "cmd|fact"),      ("🎲 /random",     "cmd|random")],
            [("◀️ Back",        "menu|main")],
        ]
    },
    "security": {
        "title": "🔐 *Security & Privacy Commands*",
        "buttons": [
            [("🔒 /encode",     "cmd|encode"),    ("🔓 /decode",     "cmd|decode")],
            [("🔒 /vault",      "cmd|vault"),     ("🛡 /checkurl",   "cmd|checkurl")],
            [("🌐 /ipinfo",     "cmd|ipinfo"),    ("🎨 /ascii",      "cmd|ascii")],
            [("◀️ Back",        "menu|main")],
        ]
    },
    "group": {
        "title": "👥 *Group Admin Commands*\n_(Use in groups only)_",
        "buttons": [
            [("👋 /welcome",    "cmd|welcome"),   ("⚠️ /warn",      "cmd|warn")],
            [("🔇 /mute",       "cmd|mute"),      ("🔊 /unmute",     "cmd|unmute")],
            [("🌊 /antiflood",  "cmd|antiflood"), ("🚨 /report",     "cmd|report")],
            [("📋 /rules",      "cmd|rules"),     ("📢 /tagall",     "cmd|tagall")],
            [("⚠️ /warnings",  "cmd|warnings"),  ("◀️ Back",        "menu|main")],
        ]
    },
    "personal": {
        "title": "⚙️ *Personalization Commands*",
        "buttons": [
            [("🏙 /setcity",    "cmd|setcity"),   ("🌐 /setlang",    "cmd|setlang")],
            [("🎨 /theme",      "cmd|theme"),     ("📊 /mystats",    "cmd|mystats")],
            [("🏆 /leaderboard","cmd|leaderboard"),("🧠 /memory",    "cmd|memory")],
            [("◀️ Back",        "menu|main")],
        ]
    },
    "admin": {
        "title": "📊 *Stats & Admin*",
        "buttons": [
            [("📊 /stats",      "cmd|stats"),     ("👥 /users",      "cmd|users")],
            [("📢 /broadcast",  "cmd|broadcast"), ("🔔 /testbrief",  "cmd|testbrief")],
            [("💬 /feedback",   "cmd|feedback"),  ("🏓 /ping",       "cmd|ping")],
            [("ℹ️ /about",     "cmd|about"),     ("◀️ Back",        "menu|main")],
        ]
    },
}


def _build_keyboard(page_key: str) -> InlineKeyboardMarkup:
    page = MENU_PAGES[page_key]
    rows = []
    for row in page["buttons"]:
        rows.append([InlineKeyboardButton(label, callback_data=cb) for label, cb in row])
    return InlineKeyboardMarkup(rows)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/menu — Interactive button menu for all commands."""
    page = MENU_PAGES["main"]
    await update.message.reply_text(
        page["title"],
        reply_markup=_build_keyboard("main"),
        parse_mode="Markdown"
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu navigation and command info buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Navigate to a menu page
    if data.startswith("menu|"):
        page_key = data.split("|")[1]
        if page_key not in MENU_PAGES:
            return
        page = MENU_PAGES[page_key]
        try:
            await query.edit_message_text(
                page["title"],
                reply_markup=_build_keyboard(page_key),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    # Show command info
    elif data.startswith("cmd|"):
        cmd = data.split("|")[1]
        await query.answer(f"Type /{cmd} to use this command!", show_alert=True)


# ── /ping ────────────────────────────────────────────────

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ping — Check if bot is alive and measure response time."""
    import time
    start = time.time()
    msg   = await update.message.reply_text("🏓 Pinging...")
    elapsed = (time.time() - start) * 1000

    now = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")

    await msg.edit_text(
        f"🏓 *Pong!*\n\n"
        f"✅ Bot is online and running!\n"
        f"⚡ Response time: *{elapsed:.0f}ms*\n"
        f"🕐 Server time: {now}\n"
        f"🤖 Version: v8.0",
        parse_mode="Markdown"
    )


# ── /feedback ────────────────────────────────────────────

def _load_feedback() -> list:
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE) as f:
            return json.load(f)
    return []


def _save_feedback(data: list):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/feedback <message> — Send feedback or bug report to Vikram."""
    if not context.args:
        await update.message.reply_text(
            "💬 *Send Feedback*\n\n"
            "`/feedback This bot is amazing!`\n"
            "`/feedback The /weather command is broken`\n"
            "`/feedback Please add voice message support`\n\n"
            "_Your feedback goes directly to Vikram!_ 🙏",
            parse_mode="Markdown"
        )
        return

    user       = update.effective_user
    message    = " ".join(context.args)
    timestamp  = datetime.now().strftime("%d %b %Y, %I:%M %p")

    # Save to file
    feedbacks = _load_feedback()
    feedbacks.append({
        "user_id":    str(user.id),
        "username":   user.username or "unknown",
        "name":       user.first_name,
        "message":    message,
        "time":       timestamp,
    })
    _save_feedback(feedbacks)

    # Forward to admin
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"💬 *New Feedback!*\n\n"
                    f"👤 From: *{user.first_name}* (@{user.username or 'no username'})\n"
                    f"🆔 ID: `{user.id}`\n"
                    f"📅 Time: {timestamp}\n\n"
                    f"📝 Message:\n_{message}_"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ *Feedback sent!*\n\n"
        f"Thank you, *{user.first_name}*! 🙏\n"
        f"Vikram will read your message soon.\n\n"
        f"_{message[:100]}_",
        parse_mode="Markdown"
    )


# ── /viewfeedback (admin only) ────────────────────────────

async def viewfeedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/viewfeedback — View all feedback. Admin only."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return

    feedbacks = _load_feedback()
    if not feedbacks:
        await update.message.reply_text("📭 No feedback received yet.")
        return

    lines = [f"💬 *All Feedback ({len(feedbacks)} messages)*\n"]
    for i, fb in enumerate(feedbacks[-10:], 1):  # Show last 10
        lines.append(
            f"*{i}.* {fb['name']} (@{fb.get('username','?')}) — {fb['time']}\n"
            f"   _{fb['message'][:100]}_\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
