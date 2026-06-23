# ============================================================
#  VIKRAM'S ADVANCED TELEGRAM BOT v8.0 — main.py
#  100+ commands | 20 handler modules
#  Render-ready with keep-alive server
# ============================================================

import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

from dotenv import load_dotenv
load_dotenv()

import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, InlineQueryHandler,
    filters, CallbackQueryHandler
)

# ── Keep-alive server for Render free tier ─────────────────
# Render needs an HTTP server to keep the service awake
# UptimeRobot pings this every 5 minutes to prevent sleeping

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            b"Babamosie Bot v8.0 is alive and running!"
        )
    def log_message(self, *args):
        pass  # Silence HTTP request logs

def run_keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
    print(f"✅ Keep-alive server running on port {port}")
    server.serve_forever()

# Start keep-alive in background thread
# Only runs when PORT env var is set (i.e. on Render)
# Does nothing when running locally
if os.environ.get("PORT"):
    threading.Thread(target=run_keep_alive, daemon=True).start()

# ── Core ───────────────────────────────────────────────────
from handlers.start          import start, help_command, about_command
from handlers.utilities      import time_command, weather_command, news_command
from handlers.jokes          import joke_command
from handlers.notes          import save_note, get_notes, clear_notes
from handlers.trivia         import trivia_command, trivia_answer
from handlers.ai             import ai_command
from handlers.social         import contact_command
from handlers.extras         import define_command, quote_command, fact_command
from handlers.persona        import persona_command, persona_callback, reset_persona_command, roleplay_chat
from handlers.reminder       import remind_command
from handlers.translate      import translate_command
from handlers.lyrics         import lyrics_command
from handlers.tools          import password_command, qr_command, poll_command, poll_callback
from handlers.admin          import broadcast_command, stats_command, users_command, register_user
from handlers.briefing       import setup_scheduler, test_briefing_command

# ── v5 features ────────────────────────────────────────────
from handlers.games          import (
    hangman_command, hangman_guess, hangman_games,
    rps_command, rps_callback,
    eightball_command, wouldyourather_command, wyr_callback,
    story_command, storyclear_command
)
from handlers.finance        import crypto_command, currency_command, stock_command
from handlers.productivity   import todo_command, calc_command, countdown_command, pomodoro_command
from handlers.utility_extras import (
    shorten_command, horoscope_command, roast_command,
    debate_command, summarize_command
)
from handlers.preferences    import (
    setcity_command, setlang_command, theme_command,
    mystats_command, leaderboard_command
)

# ── v6 features ────────────────────────────────────────────
from handlers.ai_extras      import (
    imagine_command, explain_command, code_command,
    quiz_command, quiz_callback
)
from handlers.group_admin    import (
    welcome_command, welcome_new_member,
    warn_command, warnings_command, resetwarn_command,
    mute_command, unmute_command,
    antiflood_command, check_flood,
    report_command, rules_command, tagall_command
)
from handlers.media          import (
    meme_command, movie_command,
    anime_command, youtube_command, spotify_command
)
from handlers.student_tools  import (
    flashcard_command, flashcard_callback,
    mcq_command, essay_command, formula_command
)
from handlers.automation     import (
    subscribe_command, unsubscribe_command,
    pricealert_command, check_price_alerts,
    birthday_command, check_birthdays,
    habit_command, journal_command
)
from handlers.security_fun   import (
    encode_command, decode_command, checkurl_command,
    vault_command, ipinfo_command, ascii_command,
    compliment_command, motivate_command,
    dare_command, dare_callback, ship_command
)

# ── v7 evolution ───────────────────────────────────────────
from handlers.evolution      import (
    forecast_command, topicnews_command, dictionary_command,
    tip_command, random_command, word_command,
    mathquiz_command, mathquiz_callback,
    typetest_command, typetest_check,
    agedays_command, bmi_command, emi_command,
    gpa_command, timezone_command,
)

# ── v8 NEW features ────────────────────────────────────────
from handlers.ai_advanced    import (
    memory_command, summarizeurl_command,
    rewrite_command, rewrite_callback,
    grammar_command, ask_command,
)
from handlers.menu           import (
    menu_command, menu_callback,
    ping_command, feedback_command, viewfeedback_command,
)
from handlers.student_advanced import (
    syllabus_command, pyq_command, studyplan_command,
    doubt_command, codereview_command,
)
from handlers.extras_advanced  import (
    github_command, log_command, inline_command,
    inline_query_handler,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")


# ── Middleware ─────────────────────────────────────────────

async def track_user(update, context):
    """Track every user silently."""
    if update.effective_user:
        u = update.effective_user
        register_user(u.id, u.username, u.first_name)


async def smart_message_handler(update, context):
    """Priority: Hangman → Typing test → AI chat."""
    if not update.message or not update.message.text:
        return

    text    = update.message.text.strip()
    user_id = str(update.effective_user.id)

    # Hangman: single letter while game active
    if user_id in hangman_games and len(text) == 1 and text.isalpha():
        await hangman_guess(update, context)
        return

    # Typing test: check if user is mid-test
    if await typetest_check(update, context):
        return

    # AI / persona chat
    await roleplay_chat(update, context)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ── Middleware (group -1 = before all handlers) ────────
    app.add_handler(MessageHandler(filters.ALL, track_user), group=-1)
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUPS, check_flood), group=0)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member), group=1)

    # ── Core ───────────────────────────────────────────────
    app.add_handler(CommandHandler("start",          start))
    app.add_handler(CommandHandler("help",           help_command))
    app.add_handler(CommandHandler("about",          about_command))
    app.add_handler(CommandHandler("menu",           menu_command))
    app.add_handler(CommandHandler("ping",           ping_command))
    app.add_handler(CommandHandler("feedback",       feedback_command))
    app.add_handler(CommandHandler("viewfeedback",   viewfeedback_command))

    # ── AI ─────────────────────────────────────────────────
    app.add_handler(CommandHandler("ai",             ai_command))
    app.add_handler(CommandHandler("ask",            ask_command))
    app.add_handler(CommandHandler("imagine",        imagine_command))
    app.add_handler(CommandHandler("explain",        explain_command))
    app.add_handler(CommandHandler("code",           code_command))
    app.add_handler(CommandHandler("quiz",           quiz_command))
    app.add_handler(CommandHandler("rewrite",        rewrite_command))
    app.add_handler(CommandHandler("grammar",        grammar_command))
    app.add_handler(CommandHandler("summarizeurl",   summarizeurl_command))
    app.add_handler(CommandHandler("memory",         memory_command))
    app.add_handler(CommandHandler("persona",        persona_command))
    app.add_handler(CommandHandler("resetpersona",   reset_persona_command))
    app.add_handler(CommandHandler("roast",          roast_command))
    app.add_handler(CommandHandler("debate",         debate_command))
    app.add_handler(CommandHandler("summarize",      summarize_command))
    app.add_handler(CommandHandler("story",          story_command))
    app.add_handler(CommandHandler("storyclear",     storyclear_command))

    # ── Student Tools ──────────────────────────────────────
    app.add_handler(CommandHandler("flashcard",      flashcard_command))
    app.add_handler(CommandHandler("mcq",            mcq_command))
    app.add_handler(CommandHandler("essay",          essay_command))
    app.add_handler(CommandHandler("formula",        formula_command))
    app.add_handler(CommandHandler("dictionary",     dictionary_command))
    app.add_handler(CommandHandler("define",         define_command))
    app.add_handler(CommandHandler("syllabus",       syllabus_command))
    app.add_handler(CommandHandler("pyq",            pyq_command))
    app.add_handler(CommandHandler("studyplan",      studyplan_command))
    app.add_handler(CommandHandler("doubt",          doubt_command))
    app.add_handler(CommandHandler("codereview",     codereview_command))

    # ── Utilities ──────────────────────────────────────────
    app.add_handler(CommandHandler("time",           time_command))
    app.add_handler(CommandHandler("weather",        weather_command))
    app.add_handler(CommandHandler("forecast",       forecast_command))
    app.add_handler(CommandHandler("news",           news_command))
    app.add_handler(CommandHandler("topicnews",      topicnews_command))
    app.add_handler(CommandHandler("timezone",       timezone_command))
    app.add_handler(CommandHandler("translate",      translate_command))
    app.add_handler(CommandHandler("horoscope",      horoscope_command))
    app.add_handler(CommandHandler("shorten",        shorten_command))
    app.add_handler(CommandHandler("tip",            tip_command))
    app.add_handler(CommandHandler("random",         random_command))
    app.add_handler(CommandHandler("word",           word_command))
    app.add_handler(CommandHandler("joke",           joke_command))
    app.add_handler(CommandHandler("quote",          quote_command))
    app.add_handler(CommandHandler("fact",           fact_command))
    app.add_handler(CommandHandler("lyrics",         lyrics_command))
    app.add_handler(CommandHandler("inline",         inline_command))
    app.add_handler(CommandHandler("github",         github_command))

    # ── Tools ──────────────────────────────────────────────
    app.add_handler(CommandHandler("password",       password_command))
    app.add_handler(CommandHandler("qr",             qr_command))
    app.add_handler(CommandHandler("poll",           poll_command))
    app.add_handler(CommandHandler("remind",         remind_command))
    app.add_handler(CommandHandler("encode",         encode_command))
    app.add_handler(CommandHandler("decode",         decode_command))
    app.add_handler(CommandHandler("checkurl",       checkurl_command))
    app.add_handler(CommandHandler("vault",          vault_command))
    app.add_handler(CommandHandler("ipinfo",         ipinfo_command))
    app.add_handler(CommandHandler("ascii",          ascii_command))

    # ── Notes ──────────────────────────────────────────────
    app.add_handler(CommandHandler("note",           save_note))
    app.add_handler(CommandHandler("notes",          get_notes))
    app.add_handler(CommandHandler("clearnotes",     clear_notes))

    # ── Productivity ───────────────────────────────────────
    app.add_handler(CommandHandler("todo",           todo_command))
    app.add_handler(CommandHandler("calc",           calc_command))
    app.add_handler(CommandHandler("countdown",      countdown_command))
    app.add_handler(CommandHandler("pomodoro",       pomodoro_command))
    app.add_handler(CommandHandler("typetest",       typetest_command))
    app.add_handler(CommandHandler("mathquiz",       mathquiz_command))
    app.add_handler(CommandHandler("agedays",        agedays_command))
    app.add_handler(CommandHandler("bmi",            bmi_command))
    app.add_handler(CommandHandler("emi",            emi_command))
    app.add_handler(CommandHandler("gpa",            gpa_command))

    # ── Finance ────────────────────────────────────────────
    app.add_handler(CommandHandler("crypto",         crypto_command))
    app.add_handler(CommandHandler("currency",       currency_command))
    app.add_handler(CommandHandler("stock",          stock_command))
    app.add_handler(CommandHandler("pricealert",     pricealert_command))

    # ── Games & Fun ────────────────────────────────────────
    app.add_handler(CommandHandler("trivia",         trivia_command))
    app.add_handler(CommandHandler("hangman",        hangman_command))
    app.add_handler(CommandHandler("rps",            rps_command))
    app.add_handler(CommandHandler("8ball",          eightball_command))
    app.add_handler(CommandHandler("wouldyourather", wouldyourather_command))
    app.add_handler(CommandHandler("dare",           dare_command))
    app.add_handler(CommandHandler("ship",           ship_command))
    app.add_handler(CommandHandler("compliment",     compliment_command))
    app.add_handler(CommandHandler("motivate",       motivate_command))

    # ── Media ──────────────────────────────────────────────
    app.add_handler(CommandHandler("meme",           meme_command))
    app.add_handler(CommandHandler("movie",          movie_command))
    app.add_handler(CommandHandler("anime",          anime_command))
    app.add_handler(CommandHandler("youtube",        youtube_command))
    app.add_handler(CommandHandler("spotify",        spotify_command))

    # ── Automation ─────────────────────────────────────────
    app.add_handler(CommandHandler("subscribe",      subscribe_command))
    app.add_handler(CommandHandler("unsubscribe",    unsubscribe_command))
    app.add_handler(CommandHandler("birthday",       birthday_command))
    app.add_handler(CommandHandler("habit",          habit_command))
    app.add_handler(CommandHandler("journal",        journal_command))

    # ── Group Admin ────────────────────────────────────────
    app.add_handler(CommandHandler("welcome",        welcome_command))
    app.add_handler(CommandHandler("warn",           warn_command))
    app.add_handler(CommandHandler("warnings",       warnings_command))
    app.add_handler(CommandHandler("resetwarn",      resetwarn_command))
    app.add_handler(CommandHandler("mute",           mute_command))
    app.add_handler(CommandHandler("unmute",         unmute_command))
    app.add_handler(CommandHandler("antiflood",      antiflood_command))
    app.add_handler(CommandHandler("report",         report_command))
    app.add_handler(CommandHandler("rules",          rules_command))
    app.add_handler(CommandHandler("tagall",         tagall_command))

    # ── Personalization ────────────────────────────────────
    app.add_handler(CommandHandler("setcity",        setcity_command))
    app.add_handler(CommandHandler("setlang",        setlang_command))
    app.add_handler(CommandHandler("theme",          theme_command))
    app.add_handler(CommandHandler("mystats",        mystats_command))
    app.add_handler(CommandHandler("leaderboard",    leaderboard_command))

    # ── Admin ──────────────────────────────────────────────
    app.add_handler(CommandHandler("broadcast",      broadcast_command))
    app.add_handler(CommandHandler("stats",          stats_command))
    app.add_handler(CommandHandler("users",          users_command))
    app.add_handler(CommandHandler("testbrief",      test_briefing_command))
    app.add_handler(CommandHandler("log",            log_command))
    app.add_handler(CommandHandler("contact",        contact_command))

    # ── ALL Callbacks ──────────────────────────────────────
    app.add_handler(CallbackQueryHandler(menu_callback,        pattern="^(menu|cmd)\\|"))
    app.add_handler(CallbackQueryHandler(trivia_answer,        pattern="^trivia\\|"))
    app.add_handler(CallbackQueryHandler(persona_callback,     pattern="^persona\\|"))
    app.add_handler(CallbackQueryHandler(poll_callback,        pattern="^poll"))
    app.add_handler(CallbackQueryHandler(rps_callback,         pattern="^rps\\|"))
    app.add_handler(CallbackQueryHandler(wyr_callback,         pattern="^wyr\\|"))
    app.add_handler(CallbackQueryHandler(quiz_callback,        pattern="^quiz\\|"))
    app.add_handler(CallbackQueryHandler(flashcard_callback,   pattern="^fc\\|"))
    app.add_handler(CallbackQueryHandler(dare_callback,        pattern="^dare\\|"))
    app.add_handler(CallbackQueryHandler(mathquiz_callback,    pattern="^mq\\|"))
    app.add_handler(CallbackQueryHandler(rewrite_callback,     pattern="^rw\\|"))

    # ── Inline mode ────────────────────────────────────────
    app.add_handler(InlineQueryHandler(inline_query_handler))

    # ── AI chat (catch-all text) ───────────────────────────
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, smart_message_handler
    ))

    # ── Scheduled tasks ────────────────────────────────────
    setup_scheduler(app)

    print("🤖 Vikram's Bot v8.0 is LIVE! 110+ commands ready.")
    print("📋 Type /menu to explore all features.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()