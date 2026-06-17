# ============================================================
#  handlers/preferences.py
#  /setcity <city> — Save default city for weather
#  /setlang <language> — Set preferred language
#  /theme <style> — Change bot response style
#  /mystats — Personal usage stats
#  /leaderboard — Trivia/quiz leaderboard
# ============================================================

import json
import os
from telegram import Update
from telegram.ext import ContextTypes

PREFS_FILE = "user_prefs.json"
TRIVIA_SCORES_FILE = "trivia_scores.json"


def load_prefs() -> dict:
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE) as f:
            return json.load(f)
    return {}


def save_prefs(data: dict):
    with open(PREFS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_user_pref(user_id: str, key: str, default=None):
    prefs = load_prefs()
    return prefs.get(user_id, {}).get(key, default)


def set_user_pref(user_id: str, key: str, value):
    prefs = load_prefs()
    if user_id not in prefs:
        prefs[user_id] = {}
    prefs[user_id][key] = value
    save_prefs(prefs)


# ── Trivia scores ─────────────────────────────────────────

def load_scores() -> dict:
    if os.path.exists(TRIVIA_SCORES_FILE):
        with open(TRIVIA_SCORES_FILE) as f:
            return json.load(f)
    return {}


def save_scores(data: dict):
    with open(TRIVIA_SCORES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_trivia_result(user_id: str, username: str, first_name: str, correct: bool):
    """Called by trivia handler to track scores."""
    scores = load_scores()
    if user_id not in scores:
        scores[user_id] = {"username": username, "name": first_name, "correct": 0, "total": 0}
    scores[user_id]["correct"] += 1 if correct else 0
    scores[user_id]["total"]   += 1
    scores[user_id]["name"]     = first_name  # Update in case name changed
    save_scores(scores)


# ── /setcity ─────────────────────────────────────────────

async def setcity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setcity <city> — Save your default city for /weather."""
    if not context.args:
        current = get_user_pref(str(update.effective_user.id), "city", "Not set")
        await update.message.reply_text(
            f"🏙 *Set Default City*\n\n"
            f"Current: *{current}*\n\n"
            f"Usage: `/setcity Mumbai`\n"
            f"Then `/weather` will use your city automatically!",
            parse_mode="Markdown"
        )
        return

    city = " ".join(context.args)
    set_user_pref(str(update.effective_user.id), "city", city)
    await update.message.reply_text(
        f"✅ Default city set to *{city}*!\n\n"
        f"Now `/weather` will show {city}'s weather automatically.",
        parse_mode="Markdown"
    )


# ── /setlang ─────────────────────────────────────────────

SUPPORTED_LANGS = {
    "english": "en", "hindi": "hi", "spanish": "es",
    "french": "fr", "german": "de", "tamil": "ta",
    "telugu": "te", "bengali": "bn", "marathi": "mr",
}


async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setlang <language> — Set preferred language for /translate."""
    if not context.args:
        current = get_user_pref(str(update.effective_user.id), "lang", "Not set")
        langs   = ", ".join(SUPPORTED_LANGS.keys())
        await update.message.reply_text(
            f"🌐 *Set Preferred Language*\n\n"
            f"Current: *{current}*\n\n"
            f"Available: {langs}\n\n"
            f"Usage: `/setlang Hindi`\n"
            f"Then `/translate Hello` will auto-translate to Hindi!",
            parse_mode="Markdown"
        )
        return

    lang = context.args[0].lower()
    if lang not in SUPPORTED_LANGS:
        await update.message.reply_text(
            f"❌ Unknown language: *{lang}*\n\n"
            f"Supported: {', '.join(SUPPORTED_LANGS.keys())}",
            parse_mode="Markdown"
        )
        return

    set_user_pref(str(update.effective_user.id), "lang", lang)
    await update.message.reply_text(
        f"✅ Preferred language set to *{lang.capitalize()}*!\n\n"
        f"Now `/translate Hello` will auto-translate to {lang.capitalize()}.",
        parse_mode="Markdown"
    )


# ── /theme ────────────────────────────────────────────────

THEMES = {
    "default": {"name": "🤖 Default",      "prefix": "🤖"},
    "minimal":  {"name": "⚡ Minimal",      "prefix": ""},
    "fun":      {"name": "🎉 Fun & Emoji",  "prefix": "✨"},
    "pro":      {"name": "💼 Professional", "prefix": "📌"},
    "desi":     {"name": "🇮🇳 Desi Mode",   "prefix": "🙏"},
}


async def theme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/theme <name> — Change bot response style."""
    if not context.args:
        current = get_user_pref(str(update.effective_user.id), "theme", "default")
        theme_list = "\n".join(f"• `{k}` — {v['name']}" for k, v in THEMES.items())
        await update.message.reply_text(
            f"🎨 *Bot Theme*\n\n"
            f"Current: *{THEMES.get(current, THEMES['default'])['name']}*\n\n"
            f"Available themes:\n{theme_list}\n\n"
            f"Usage: `/theme fun`",
            parse_mode="Markdown"
        )
        return

    theme = context.args[0].lower()
    if theme not in THEMES:
        await update.message.reply_text(
            f"❌ Unknown theme: `{theme}`\n\n"
            f"Available: {', '.join(THEMES.keys())}",
            parse_mode="Markdown"
        )
        return

    set_user_pref(str(update.effective_user.id), "theme", theme)
    t = THEMES[theme]
    await update.message.reply_text(
        f"🎨 Theme changed to *{t['name']}*! {t['prefix']}\n\n"
        f"_Your AI responses will now use this style._",
        parse_mode="Markdown"
    )


# ── /mystats ─────────────────────────────────────────────

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mystats — Your personal bot usage stats."""
    user_id  = str(update.effective_user.id)
    user     = update.effective_user

    # Load from users_db
    users_db = {}
    if os.path.exists("users_db.json"):
        with open("users_db.json") as f:
            users_db = json.load(f)

    # Load trivia scores
    scores   = load_scores()
    prefs    = load_prefs().get(user_id, {})

    u_data   = users_db.get(user_id, {})
    msgs     = u_data.get("messages", 0)
    joined   = u_data.get("joined", "Unknown")

    t_data   = scores.get(user_id, {})
    t_correct = t_data.get("correct", 0)
    t_total  = t_data.get("total", 0)
    t_pct    = f"{t_correct/t_total*100:.0f}%" if t_total > 0 else "N/A"

    city  = prefs.get("city",  "Not set")
    lang  = prefs.get("lang",  "Not set")
    theme = prefs.get("theme", "default")

    # Load notes count
    notes_count = 0
    if os.path.exists("notes_db.json"):
        with open("notes_db.json") as f:
            notes = json.load(f)
        notes_count = len(notes.get(user_id, []))

    await update.message.reply_text(
        f"📊 *Your Stats — {user.first_name}*\n\n"
        f"💬 Messages sent: *{msgs}*\n"
        f"📅 First used: {joined}\n"
        f"📝 Notes saved: *{notes_count}*\n\n"
        f"🎮 *Trivia:*\n"
        f"  Correct: {t_correct}/{t_total} ({t_pct})\n\n"
        f"⚙️ *Preferences:*\n"
        f"  🏙 City: {city}\n"
        f"  🌐 Language: {lang}\n"
        f"  🎨 Theme: {theme}",
        parse_mode="Markdown"
    )


# ── /leaderboard ─────────────────────────────────────────

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/leaderboard — Top trivia scorers."""
    scores = load_scores()

    if not scores:
        await update.message.reply_text(
            "🏆 No trivia scores yet!\n\n"
            "Play some trivia first: /trivia"
        )
        return

    # Sort by correct answers, then accuracy
    sorted_scores = sorted(
        scores.items(),
        key=lambda x: (x[1].get("correct", 0), x[1].get("total", 0)),
        reverse=True
    )[:10]

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines  = ["🏆 *Trivia Leaderboard — Top 10*\n"]

    for i, (uid, data) in enumerate(sorted_scores):
        name    = data.get("name", "Unknown")
        correct = data.get("correct", 0)
        total   = data.get("total", 0)
        pct     = f"{correct/total*100:.0f}%" if total > 0 else "0%"
        medal   = medals[i]
        lines.append(f"{medal} *{name}* — {correct}/{total} ({pct})")

    lines.append("\nPlay more trivia: /trivia")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
