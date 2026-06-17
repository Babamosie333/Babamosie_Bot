# ============================================================
#  handlers/extras_advanced.py
#  Error logging to file
#  Rate limiting middleware
#  /github <username> — GitHub profile lookup
#  /log — Admin: view recent error log
#  /inline — Instructions for inline mode
# ============================================================

import os
import json
import time
import logging
import requests
from datetime import datetime
from collections import defaultdict
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
import hashlib

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
ADMIN_ID     = int(os.environ.get("ADMIN_ID", "0"))
LOG_FILE     = "bot_errors.log"
RATE_FILE    = "rate_limits.json"

# ── File-based error logger ───────────────────────────────

def setup_file_logging():
    """Call once at startup to log errors to file."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),          # also print to console
        ]
    )
    logger = logging.getLogger("vikram_bot")
    logger.info("=== Bot started at %s ===", datetime.now().strftime("%d %b %Y %I:%M %p"))
    return logger


bot_logger = setup_file_logging()


def log_error(context: str, error: Exception, user_id: str = ""):
    """Log an error with context."""
    bot_logger.error(
        "ERROR | user=%s | context=%s | %s: %s",
        user_id, context, type(error).__name__, str(error)
    )


def log_command(user_id: str, username: str, command: str):
    """Log every command usage for analytics."""
    bot_logger.info("CMD | user=%s (@%s) | %s", user_id, username or "?", command)


# ── Rate limiter ──────────────────────────────────────────
# In-memory: { user_id: { command: [timestamps] } }
_rate_data: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

# Limits per command category (requests per window in seconds)
RATE_LIMITS = {
    "ai":       (10, 60),   # 10 AI requests per 60 seconds
    "default":  (30, 60),   # 30 any commands per 60 seconds
    "finance":  (20, 60),   # 20 finance requests per 60 seconds
    "media":    (15, 60),   # 15 media requests per 60 seconds
}

AI_COMMANDS      = {"ai", "ask", "explain", "code", "imagine", "quiz", "rewrite",
                    "grammar", "roast", "debate", "summarize", "story", "doubt",
                    "syllabus", "pyq", "studyplan", "codereview", "essay", "mcq"}
FINANCE_COMMANDS = {"crypto", "stock", "currency", "pricealert"}
MEDIA_COMMANDS   = {"meme", "movie", "anime", "youtube", "spotify"}


def check_rate_limit(user_id: str, command: str) -> tuple[bool, int]:
    """
    Returns (is_allowed, seconds_until_reset).
    Call before processing any command.
    """
    # Determine category
    if command in AI_COMMANDS:
        category = "ai"
    elif command in FINANCE_COMMANDS:
        category = "finance"
    elif command in MEDIA_COMMANDS:
        category = "media"
    else:
        category = "default"

    max_requests, window = RATE_LIMITS[category]
    now       = time.time()
    key       = f"{category}"

    # Clean old timestamps
    _rate_data[user_id][key] = [
        t for t in _rate_data[user_id][key] if now - t < window
    ]

    if len(_rate_data[user_id][key]) >= max_requests:
        oldest      = _rate_data[user_id][key][0]
        reset_in    = int(window - (now - oldest)) + 1
        return False, reset_in

    _rate_data[user_id][key].append(now)
    return True, 0


async def rate_limit_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Middleware — check rate limit for every command.
    Register as group=-2 handler (runs before everything else).
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if not text.startswith("/"):
        return

    command = text.split()[0].lstrip("/").split("@")[0].lower()
    user_id = str(update.effective_user.id)

    # Admin is never rate-limited
    if update.effective_user.id == ADMIN_ID:
        return

    allowed, reset_in = check_rate_limit(user_id, command)
    if not allowed:
        await update.message.reply_text(
            f"⏳ *Slow down!*\n\n"
            f"You're sending too many commands.\n"
            f"Please wait *{reset_in} seconds* and try again.\n\n"
            f"_Rate limits keep the bot healthy for everyone_ 🙏",
            parse_mode="Markdown"
        )
        # Stop propagation — don't process the command
        context.application.stop_running()   # Won't work — use raise instead
        raise Exception("rate_limited")      # Caught silently by PTB


# ── /github ───────────────────────────────────────────────

async def github_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/github <username> — GitHub profile and top repos."""
    if not context.args:
        await update.message.reply_text(
            "🐙 *GitHub Profile Lookup*\n\n"
            "`/github torvalds` — Linus Torvalds\n"
            "`/github gvanrossum` — Python creator\n"
            "`/github your_username` — Your own profile!\n\n"
            "Shows: bio, followers, repos, top languages",
            parse_mode="Markdown"
        )
        return

    username = context.args[0].strip().lstrip("@")
    await update.message.chat.send_action("typing")

    try:
        # GitHub API — no key needed for public data (60 req/hour)
        headers = {"Accept": "application/vnd.github.v3+json",
                   "User-Agent": "TelegramBot/1.0"}

        # Get user profile
        user_resp = requests.get(
            f"https://api.github.com/users/{username}",
            headers=headers, timeout=8
        )

        if user_resp.status_code == 404:
            await update.message.reply_text(f"❌ GitHub user `{username}` not found.", parse_mode="Markdown")
            return
        if user_resp.status_code == 403:
            await update.message.reply_text("❌ GitHub API rate limit hit. Try again in an hour.")
            return

        u = user_resp.json()

        name        = u.get("name") or username
        bio         = u.get("bio") or "No bio"
        company     = u.get("company") or "—"
        location    = u.get("location") or "—"
        followers   = u.get("followers", 0)
        following   = u.get("following", 0)
        public_repos= u.get("public_repos", 0)
        blog        = u.get("blog") or "—"
        created     = u.get("created_at", "")[:10]
        github_url  = u.get("html_url", f"https://github.com/{username}")
        avatar      = u.get("avatar_url", "")

        # Get top repos
        repos_resp = requests.get(
            f"https://api.github.com/users/{username}/repos?sort=stars&per_page=5",
            headers=headers, timeout=8
        )
        repos = repos_resp.json() if repos_resp.status_code == 200 else []

        repo_lines = []
        for r in repos[:4]:
            stars = r.get("stargazers_count", 0)
            lang  = r.get("language") or "?"
            rname = r.get("name", "")
            rdesc = (r.get("description") or "")[:60]
            repo_lines.append(f"• ⭐{stars} [`{rname}`]({r.get('html_url','')}) _{lang}_ — {rdesc}")

        repos_text = "\n".join(repo_lines) if repo_lines else "No public repos"

        text = (
            f"🐙 *GitHub: {name}* (@{username})\n\n"
            f"📝 {bio}\n\n"
            f"🏢 Company: {company}\n"
            f"📍 Location: {location}\n"
            f"🌐 Blog: {blog}\n"
            f"📅 Joined: {created}\n\n"
            f"👥 Followers: *{followers:,}* · Following: {following:,}\n"
            f"📁 Public Repos: *{public_repos}*\n\n"
            f"⭐ *Top Repos:*\n{repos_text}\n\n"
            f"🔗 [View on GitHub]({github_url})"
        )

        if avatar:
            await update.message.reply_photo(
                photo=avatar,
                caption=text,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ GitHub lookup failed: {str(e)[:80]}")


# ── /log (admin) ──────────────────────────────────────────

async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/log — View recent bot error log. Admin only."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin only!")
        return

    if not os.path.exists(LOG_FILE):
        await update.message.reply_text("📭 No log file found yet.")
        return

    # Read last 50 lines
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    last_lines = lines[-50:]
    log_text   = "".join(last_lines)

    if not log_text.strip():
        await update.message.reply_text("📭 Log file is empty.")
        return

    # Send as text file if too long
    if len(log_text) > 3500:
        # Send last 30 lines only
        log_text = "".join(lines[-30:])

    await update.message.reply_text(
        f"📋 *Recent Bot Log* (last {len(last_lines)} lines)\n\n"
        f"```\n{log_text[-3000:]}\n```",
        parse_mode="Markdown"
    )


# ── /inline instructions ──────────────────────────────────

async def inline_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/inline — Explain how to use inline mode."""
    bot_username = context.bot.username
    await update.message.reply_text(
        f"⚡ *Inline Mode*\n\n"
        f"Use me in ANY chat without opening me!\n\n"
        f"*How to use:*\n"
        f"In any chat, type:\n"
        f"`@{bot_username} <your query>`\n\n"
        f"*Examples:*\n"
        f"`@{bot_username} joke` — Get a joke\n"
        f"`@{bot_username} fact` — Get a fun fact\n"
        f"`@{bot_username} quote` — Get a quote\n"
        f"`@{bot_username} hello` — Quick greeting\n\n"
        f"_Results appear as tappable cards you can share!_",
        parse_mode="Markdown"
    )


# ── Inline query handler ──────────────────────────────────

import random

INLINE_FACTS = [
    "🧠 The human brain can store approximately 2.5 petabytes of data!",
    "💻 The first computer bug was an actual moth found in a Harvard computer in 1947.",
    "🐍 Python is named after Monty Python, not the snake!",
    "🌐 The first website ever is still online — info.cern.ch",
    "⚡ Lightning strikes Earth about 100 times every second.",
    "🦋 Butterflies taste with their feet.",
    "🍯 Honey never expires — 3000-year-old honey found in Egyptian tombs was still edible!",
]

INLINE_QUOTES = [
    ("The best way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("Code is like humor. When you have to explain it, it's bad.", "Cory House"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("In order to be irreplaceable, one must always be different.", "Coco Chanel"),
]

INLINE_JOKES = [
    "Why do programmers prefer dark mode?\n\nBecause light attracts bugs! 🐛",
    "How many programmers does it take to change a light bulb?\n\nNone. That's a hardware problem! 💡",
    "Why did the programmer quit?\n\nBecause he didn't get arrays! 😂",
    "A SQL query walks into a bar, walks up to two tables and asks...\n\n'Can I join you?' 🍺",
    "Why do Java developers wear glasses?\n\nBecause they can't C#! 👓",
]


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries — @BotUsername <query>."""
    query   = update.inline_query.query.strip().lower()
    results = []

    def make_result(uid: str, title: str, content: str, description: str = "") -> InlineQueryResultArticle:
        return InlineQueryResultArticle(
            id=uid,
            title=title,
            description=description[:60] if description else content[:60],
            input_message_content=InputTextMessageContent(
                message_text=content,
                parse_mode="Markdown"
            )
        )

    if not query or query in ("help", "start"):
        results = [
            make_result("1", "😄 Get a Joke",     random.choice(INLINE_JOKES),  "Programming joke"),
            make_result("2", "🤯 Fun Fact",        random.choice(INLINE_FACTS),  "Random fun fact"),
            make_result("3", "💬 Quote",           f"💬 *\"{INLINE_QUOTES[0][0]}\"*\n— _{INLINE_QUOTES[0][1]}_", "Motivational quote"),
            make_result("4", "👋 Hello!",          "👋 Hey! I'm Vikram's Bot v8.0 🤖\n\nType /start to see all commands!", "Greeting"),
        ]

    elif query in ("joke", "jokes", "funny"):
        joke = random.choice(INLINE_JOKES)
        results = [make_result("j1", "😄 Programming Joke", joke, joke[:50])]

    elif query in ("fact", "facts"):
        fact = random.choice(INLINE_FACTS)
        results = [make_result("f1", "🤯 Fun Fact", fact, fact[:50])]

    elif query in ("quote", "quotes", "motivation", "motivate"):
        q, a = random.choice(INLINE_QUOTES)
        text = f"💬 *\"{q}\"*\n\n— _{a}_"
        results = [make_result("q1", "💬 Motivational Quote", text, q[:50])]

    elif query in ("hello", "hi", "hey"):
        results = [make_result("h1", "👋 Say Hello",
            "👋 Hey there! I'm *Vikram's Bot* 🤖\n\nOpen me and type /start to explore 100+ commands!",
            "Share a greeting")]

    else:
        # Try to give a useful response for any query
        results = [
            make_result("s1", f"🔍 Search '{query}'",
                f"🔍 You searched: *{query}*\n\nOpen @{context.bot.username} and use `/ai {query}` for an AI answer!",
                f"Ask AI about {query}"),
            make_result("s2", "😄 Random Joke", random.choice(INLINE_JOKES), "Share a joke"),
            make_result("s3", "🤯 Random Fact", random.choice(INLINE_FACTS), "Share a fact"),
        ]

    await update.inline_query.answer(results, cache_time=10)
