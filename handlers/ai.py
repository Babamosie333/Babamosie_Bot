# ============================================================
#  handlers/ai.py  (UPDATED — uses Groq FREE API)
#
#  Groq is 100% free with no credit card needed!
#
#  HOW TO GET YOUR FREE GROQ API KEY:
#    1. Go to https://console.groq.com
#    2. Sign up with Google/GitHub (free)
#    3. Click "API Keys" → "Create API Key"
#    4. Copy the key (starts with gsk_...)
#    5. Set it as environment variable: GROQ_API_KEY
#
#  Free limits: 30 requests/min, 14,400 requests/day
#  That's more than enough for a student project bot!
# ============================================================

import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

# ── API Key ───────────────────────────────────────────────
# Set this as an environment variable — never hardcode keys!
#
# Locally (Linux/Mac):   export GROQ_API_KEY="gsk_your_key_here"
# Locally (Windows CMD): set GROQ_API_KEY=gsk_your_key_here
# On Railway:            Add GROQ_API_KEY in the Variables tab
# ─────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")

# ── Groq API endpoint ─────────────────────────────────────
# Groq uses the same format as OpenAI, so it's easy to use
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ── Model choice ──────────────────────────────────────────
# llama3-8b-8192  → fastest, lightest  (recommended for bots)
# llama3-70b-8192 → smarter but slower
# mixtral-8x7b    → good balance
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Per-user conversation history ─────────────────────────
# Stores last N messages per user so AI remembers context
# Format: { "user_id": [ {"role": "user", "content": "..."}, ... ] }
conversation_history: dict[str, list] = {}

# How many messages to remember per user (keep this low to save tokens)
MAX_HISTORY = 10

# ── System prompt ─────────────────────────────────────────
# This sets the AI's personality and behavior
SYSTEM_PROMPT = """You are Jarvis, a helpful and friendly Telegram bot assistant.
You help users with questions, coding doubts, homework, general knowledge, and more.
Keep answers concise and clear — this is a Telegram chat, not a long essay.
Use simple, easy-to-understand language.
The user is likely a BCA (Bachelor of Computer Applications) student in India,
so you can use basic tech terms but explain advanced ones.
If someone greets you, greet them back warmly.
Use emojis occasionally to keep the tone friendly."""


# ============================================================
#  Core AI function — sends message to Groq, gets reply
# ============================================================

def ask_groq(user_id: str, user_message: str, system_override: str = None) -> str:
    """
    Send a message to Groq's free LLaMA API and return the reply.
    Maintains per-user conversation history for context-aware replies.
    Optional system_override injects memory context.
    """

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]

    messages = [
        {"role": "system", "content": system_override or SYSTEM_PROMPT}
    ] + conversation_history[user_id]

    # ── Make the API request ──────────────────────────────
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",   # Your API key
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 500,          # Keep replies short for Telegram
        "temperature": 0.7,         # 0 = very factual, 1 = more creative
        "stream": False             # We want the full reply at once, not streamed
    }

    response = requests.post(
        GROQ_API_URL,
        headers=headers,
        json=payload,
        timeout=20                  # Wait max 20 seconds before giving up
    )

    # ── Handle non-200 responses ──────────────────────────
    if response.status_code == 401:
        return "❌ Invalid API key. Check your GROQ_API_KEY environment variable."
    elif response.status_code == 429:
        return "⏳ Too many requests! Groq free limit hit. Please wait a minute and try again."
    elif response.status_code != 200:
        return f"❌ Groq API error {response.status_code}. Try again later."

    # ── Parse the response ────────────────────────────────
    data  = response.json()
    reply = data["choices"][0]["message"]["content"]

    # Add AI's reply to history so next message has full context
    conversation_history[user_id].append({
        "role": "assistant",
        "content": reply
    })

    return reply


# ============================================================
#  Telegram command & message handlers
# ============================================================

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ai <question> — Explicitly ask the AI something.
    Example: /ai What is polymorphism in OOP?
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide a question after /ai\n\n"
            "Example: `/ai Explain recursion simply`\n\n"
            "Or just *type any message* directly — I'll reply with AI! 🤖",
            parse_mode="Markdown"
        )
        return

    question = " ".join(context.args)    # Join all words after /ai into one string
    await _send_ai_reply(update, question)


async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles any plain text message (not starting with /).
    Routes it to the AI automatically — makes the bot feel like a real chat!
    """
    user_text = update.message.text
    await _send_ai_reply(update, user_text)


async def _send_ai_reply(update: Update, question: str):
    """
    Shared helper used by both ai_command() and handle_ai_message().
    Shows typing indicator → injects memory → calls AI → saves memory → sends reply.
    """
    user_id = str(update.effective_user.id)

    await update.message.chat.send_action("typing")

    # Inject long-term memory into system prompt
    try:
        from handlers.ai_advanced import get_user_memory_context, update_memory_from_conversation
        memory_ctx = get_user_memory_context(user_id)
        system     = SYSTEM_PROMPT + (f"\n\n{memory_ctx}" if memory_ctx else "")
    except Exception:
        system     = SYSTEM_PROMPT
        memory_ctx = ""

    try:
        reply = ask_groq(user_id, question, system_override=system)

        # Update long-term memory from this exchange
        try:
            from handlers.ai_advanced import update_memory_from_conversation
            update_memory_from_conversation(user_id, question, reply)
        except Exception:
            pass

        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i:i+4000])
        else:
            await update.message.reply_text(f"🤖 {reply}")

    except requests.Timeout:
        await update.message.reply_text(
            "⏳ The AI is taking too long to respond. Try again in a moment!"
        )
    except requests.ConnectionError:
        await update.message.reply_text(
            "🌐 Connection error! Check your internet or try again later."
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Something went wrong with the AI. Try /joke or /trivia meanwhile! 😊"
        )


# ============================================================
#  ENVIRONMENT VARIABLES SUMMARY
#
#  Variable        Where to get it
#  ─────────────────────────────────────────────────────────
#  GROQ_API_KEY    https://console.groq.com → API Keys
#  BOT_TOKEN       Telegram @BotFather → /newbot
#
#  On Railway:
#    Dashboard → Your Project → Variables tab → Add both
#
#  Locally (Mac/Linux):
#    export GROQ_API_KEY="gsk_..."
#    export BOT_TOKEN="123456:ABC..."
#    python main.py
#
#  Locally (Windows):
#    set GROQ_API_KEY=gsk_...
#    set BOT_TOKEN=123456:ABC...
#    python main.py
# ============================================================
