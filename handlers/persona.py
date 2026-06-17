# ============================================================
#  handlers/persona.py
#  /persona — Switch AI personality/roleplay mode
#  /resetpersona — Go back to default Jarvis mode
# ============================================================

import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── Available personas ────────────────────────────────────
PERSONAS = {
    "jarvis": {
        "name":  "🤖 Jarvis (Default)",
        "emoji": "🤖",
        "prompt": (
            "You are Jarvis, a helpful and friendly AI assistant for a BCA student in India. "
            "Answer questions clearly and concisely. Use simple language and occasional emojis."
        ),
    },
    "professor": {
        "name":  "👨‍🏫 Strict Professor",
        "emoji": "👨‍🏫",
        "prompt": (
            "You are a strict but knowledgeable Computer Science professor. "
            "You explain topics thoroughly, use technical terms, and always encourage the student to think deeper. "
            "You occasionally quiz the student back with follow-up questions. Be formal but supportive."
        ),
    },
    "friend": {
        "name":  "😎 Cool Senior Dev Friend",
        "emoji": "😎",
        "prompt": (
            "You are a cool senior software developer who is the user's best friend. "
            "You talk casually, use slang sometimes, crack programming jokes, "
            "and give real-world practical advice. You call the user 'bro' or 'yaar'. "
            "You're very encouraging and always say things like 'arre easy hai yaar' or 'chill bro'."
        ),
    },
    "interviewer": {
        "name":  "💼 HR Interviewer",
        "emoji": "💼",
        "prompt": (
            "You are a professional HR interviewer conducting a mock technical interview for a BCA fresher. "
            "Ask one interview question at a time, wait for the answer, give constructive feedback, "
            "then ask the next question. Cover topics like OOP, DBMS, OS, networking, and HR questions. "
            "Be professional but encouraging. Start by introducing yourself and asking the candidate to introduce themselves."
        ),
    },
    "comedian": {
        "name":  "🤣 Stand-up Comedian",
        "emoji": "🤣",
        "prompt": (
            "You are a hilarious stand-up comedian who happens to know a lot about technology and programming. "
            "Answer every question with humour, puns, and jokes. Make the user laugh while still being helpful. "
            "Use lots of wordplay. Keep responses funny and light."
        ),
    },
    "mentor": {
        "name":  "🧘 Life & Career Mentor",
        "emoji": "🧘",
        "prompt": (
            "You are a wise life and career mentor for young tech students in India. "
            "Give advice on career growth, learning paths, motivation, work-life balance, "
            "and how to succeed as a developer. Be warm, thoughtful, and inspiring. "
            "Reference Indian tech culture and opportunities when relevant."
        ),
    },
}

# Stores the active persona per user: { "user_id": "persona_key" }
active_personas: dict[str, str] = {}

# Per-persona conversation history per user
persona_history: dict[str, list] = {}


def get_persona_key(user_id: str) -> str:
    """Return the active persona key for a user, default to 'jarvis'."""
    return active_personas.get(user_id, "jarvis")


async def persona_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/persona — Show persona selection menu as tap buttons."""
    text = (
        "🎭 *Choose a Persona*\n\n"
        "Switch my personality! Tap one below:\n"
    )

    keyboard = []
    for key, p in PERSONAS.items():
        keyboard.append([
            InlineKeyboardButton(p["name"], callback_data=f"persona|{key}")
        ])

    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def persona_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles persona button taps."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("persona|"):
        return

    key     = query.data.split("|")[1]
    user_id = str(query.from_user.id)
    persona = PERSONAS.get(key)

    if not persona:
        await query.edit_message_text("❌ Unknown persona. Try /persona again.")
        return

    # Set the persona and clear old conversation history
    active_personas[user_id] = key
    persona_history[user_id] = []

    await query.edit_message_text(
        f"{persona['emoji']} *Persona switched to: {persona['name']}*\n\n"
        f"Now just talk to me — I'll respond in character!\n"
        f"To go back to default: /resetpersona",
        parse_mode="Markdown"
    )


async def reset_persona_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resetpersona — Reset back to default Jarvis persona."""
    user_id = str(update.effective_user.id)
    active_personas[user_id] = "jarvis"
    persona_history[user_id] = []
    await update.message.reply_text(
        "🤖 Persona reset to *Jarvis* (default)!\n"
        "I'm back to my normal helpful self. 😊",
        parse_mode="Markdown"
    )


async def roleplay_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle AI messages using the active persona.
    Called from ai.py's handle_ai_message for all plain text.
    """
    user_id  = str(update.effective_user.id)
    user_msg = update.message.text
    key      = get_persona_key(user_id)
    persona  = PERSONAS[key]

    await update.message.chat.send_action("typing")

    # Initialize history for this user
    if user_id not in persona_history:
        persona_history[user_id] = []

    persona_history[user_id].append({"role": "user", "content": user_msg})

    # Trim history
    if len(persona_history[user_id]) > 12:
        persona_history[user_id] = persona_history[user_id][-12:]

    messages = [{"role": "system", "content": persona["prompt"]}] + persona_history[user_id]

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.8,
                "stream": False
            },
            timeout=20
        )

        if resp.status_code == 429:
            await update.message.reply_text("⏳ Rate limit hit. Wait a moment and try again.")
            return
        if resp.status_code != 200:
            await update.message.reply_text(f"❌ Groq API error {resp.status_code}. Try again.")
            return

        reply = resp.json()["choices"][0]["message"]["content"]
        persona_history[user_id].append({"role": "assistant", "content": reply})

        # Show which persona is active (subtle indicator)
        prefix = persona["emoji"] if key != "jarvis" else "🤖"
        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i:i+4000])
        else:
            await update.message.reply_text(f"{prefix} {reply}")

    except requests.Timeout:
        await update.message.reply_text("⏳ AI taking too long. Try again!")
    except Exception:
        await update.message.reply_text("❌ Something went wrong. Try again!")
