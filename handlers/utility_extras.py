# ============================================================
#  handlers/utility_extras.py
#  /shorten <url> — URL shortener
#  /horoscope <sign> — Daily horoscope
#  /roast — AI roast generator
#  /debate <topic> — AI debates both sides
#  /summarize <text> — Summarize long text
# ============================================================

import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


def _ask_groq_simple(system: str, user: str, max_tokens: int = 400) -> str:
    resp = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.8,
        },
        timeout=20
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── URL Shortener ─────────────────────────────────────────

async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shorten <url> — Shorten any URL using TinyURL (free, no key)."""
    if not context.args:
        await update.message.reply_text(
            "🔗 *URL Shortener*\n\n"
            "`/shorten https://www.google.com`\n"
            "`/shorten https://github.com/your/repo`",
            parse_mode="Markdown"
        )
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    await update.message.chat.send_action("typing")

    try:
        resp = requests.get(
            f"https://tinyurl.com/api-create.php?url={requests.utils.quote(url)}",
            timeout=8
        )
        if resp.status_code == 200 and resp.text.startswith("http"):
            short = resp.text.strip()
            await update.message.reply_text(
                f"🔗 *URL Shortened!*\n\n"
                f"Original: `{url[:60]}{'...' if len(url)>60 else ''}`\n\n"
                f"Short URL: {short}\n\n"
                f"_(Tap to copy!)_",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Could not shorten that URL. Make sure it's valid.")
    except Exception:
        await update.message.reply_text("❌ URL shortener unavailable. Try again later.")


# ── Horoscope ─────────────────────────────────────────────

ZODIAC_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

ZODIAC_EMOJI = {
    "aries": "♈", "taurus": "♉", "gemini": "♊", "cancer": "♋",
    "leo": "♌", "virgo": "♍", "libra": "♎", "scorpio": "♏",
    "sagittarius": "♐", "capricorn": "♑", "aquarius": "♒", "pisces": "♓",
}

ZODIAC_HINDI = {
    "aries":       "मेष (Mesh)",
    "taurus":      "वृषभ (Vrishabh)",
    "gemini":      "मिथुन (Mithun)",
    "cancer":      "कर्क (Kark)",
    "leo":         "सिंह (Singh)",
    "virgo":       "कन्या (Kanya)",
    "libra":       "तुला (Tula)",
    "scorpio":     "वृश्चिक (Vrishchik)",
    "sagittarius": "धनु (Dhanu)",
    "capricorn":   "मकर (Makar)",
    "aquarius":    "कुंभ (Kumbh)",
    "pisces":      "मीन (Meen)",
}

ZODIAC_DATES = {
    "aries": "Mar 21 – Apr 19", "taurus": "Apr 20 – May 20",
    "gemini": "May 21 – Jun 20", "cancer": "Jun 21 – Jul 22",
    "leo": "Jul 23 – Aug 22", "virgo": "Aug 23 – Sep 22",
    "libra": "Sep 23 – Oct 22", "scorpio": "Oct 23 – Nov 21",
    "sagittarius": "Nov 22 – Dec 21", "capricorn": "Dec 22 – Jan 19",
    "aquarius": "Jan 20 – Feb 18", "pisces": "Feb 19 – Mar 20",
}

# Also accept Hindi romanized input
ZODIAC_HINDI_ALIASES = {
    "mesh": "aries", "vrishabh": "taurus", "mithun": "gemini",
    "kark": "cancer", "singh": "leo", "kanya": "virgo",
    "tula": "libra", "vrishchik": "scorpio", "dhanu": "sagittarius",
    "makar": "capricorn", "kumbh": "aquarius", "meen": "pisces",
}


async def horoscope_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/horoscope <sign> — Daily horoscope in English + Hindi."""
    if not context.args:
        lines = []
        for s in ZODIAC_SIGNS:
            lines.append(f"{ZODIAC_EMOJI[s]} *{s.capitalize()}* — {ZODIAC_HINDI[s]}")
        signs_list = "\n".join(lines)
        await update.message.reply_text(
            f"🔮 *Daily Horoscope / राशिफल*\n\n"
            f"अपनी राशि चुनें (Pick your sign):\n\n"
            f"{signs_list}\n\n"
            f"Example: `/horoscope leo` or `/horoscope singh`",
            parse_mode="Markdown"
        )
        return

    sign_input = context.args[0].lower()

    # Accept English or Hindi romanized names
    sign = ZODIAC_HINDI_ALIASES.get(sign_input, sign_input)

    if sign not in ZODIAC_SIGNS:
        await update.message.reply_text(
            f"❌ Unknown sign: *{sign_input}*\n\n"
            f"Try English: aries, leo, cancer...\n"
            f"या Hindi में: mesh, singh, kark...",
            parse_mode="Markdown"
        )
        return

    await update.message.chat.send_action("typing")

    try:
        emoji      = ZODIAC_EMOJI[sign]
        dates      = ZODIAC_DATES[sign]
        hindi_name = ZODIAC_HINDI[sign]

        horoscope = _ask_groq_simple(
            system=(
                "You are a mystical but practical astrologer. "
                "Write a short, fun, and uplifting daily horoscope for the given zodiac sign. "
                "Structure it EXACTLY like this (use these exact emoji labels):\n"
                "⚡ Today's Energy: [1 sentence]\n"
                "❤️ Love & Relations: [1 sentence]\n"
                "📚 Career & Studies: [1 sentence]\n"
                "🍀 Lucky Number: [number]  |  🎨 Lucky Color: [color]\n\n"
                "Keep it positive, specific, and believable."
            ),
            user=f"Write today's horoscope for {sign.capitalize()}.",
            max_tokens=220
        )

        await update.message.reply_text(
            f"{emoji} *{sign.capitalize()} — {hindi_name}*\n"
            f"📅 _{dates}_\n\n"
            f"{horoscope}\n\n"
            f"_✨ May the stars guide you! शुभकामनाएं! 🙏_",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Horoscope service unavailable. Try again!")


# ── AI Roast ─────────────────────────────────────────────

async def roast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/roast [name or topic] — Get a playful AI roast."""
    target = " ".join(context.args) if context.args else update.effective_user.first_name
    await update.message.chat.send_action("typing")

    try:
        roast = _ask_groq_simple(
            system=(
                "You are a friendly roast comedian — like a comedy roast at a party. "
                "Write a short (3-4 sentences), PLAYFUL and FUNNY roast. "
                "Keep it good-natured, NOT mean or offensive. "
                "Include tech/student/India references if relevant. No profanity."
            ),
            user=f"Roast: {target}",
            max_tokens=200
        )
        await update.message.reply_text(
            f"🔥 *Roasting {target}...*\n\n{roast}\n\n"
            f"😂 _All in good fun!_",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Roast AI is taking a break. Try again!")


# ── AI Debate ─────────────────────────────────────────────

async def debate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/debate <topic> — AI argues both sides of a topic."""
    if not context.args:
        await update.message.reply_text(
            "⚖️ *AI Debate*\n\n"
            "I'll argue BOTH sides of any topic!\n\n"
            "`/debate Python vs JavaScript`\n"
            "`/debate Social media is good`\n"
            "`/debate Work from home`\n"
            "`/debate AI will take our jobs`",
            parse_mode="Markdown"
        )
        return

    topic = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        debate = _ask_groq_simple(
            system=(
                "You are a balanced debate moderator. "
                "Present BOTH sides of the topic clearly. "
                "Format your response as:\n"
                "✅ FOR: [3 strong points supporting the topic]\n\n"
                "❌ AGAINST: [3 strong points opposing the topic]\n\n"
                "⚖️ VERDICT: [1 balanced conclusion sentence]\n\n"
                "Keep each point to 1-2 sentences. Be fair and logical."
            ),
            user=f"Debate topic: {topic}",
            max_tokens=450
        )
        await update.message.reply_text(
            f"⚖️ *Debate: {topic}*\n\n{debate}",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Debate AI unavailable. Try again!")


# ── AI Summarizer ─────────────────────────────────────────

async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/summarize <text or URL> — Summarize long text with AI."""
    if not context.args:
        await update.message.reply_text(
            "📝 *AI Summarizer*\n\n"
            "Paste any long text after the command:\n\n"
            "`/summarize <your long text here>`\n\n"
            "Works great for:\n"
            "• Long articles\n"
            "• Study notes\n"
            "• News paragraphs\n"
            "• Assignment descriptions",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    if len(text) < 50:
        await update.message.reply_text("❌ Text is too short to summarize! Need at least 50 characters.")
        return

    await update.message.chat.send_action("typing")

    try:
        summary = _ask_groq_simple(
            system=(
                "You are a professional summarizer. "
                "Create a concise, clear summary of the given text. "
                "Format:\n"
                "📌 Main Point: [1 sentence]\n"
                "🔑 Key Points: [3-5 bullet points]\n"
                "💡 Takeaway: [1 sentence]\n\n"
                "Be brief and accurate."
            ),
            user=f"Summarize this:\n\n{text}",
            max_tokens=350
        )
        await update.message.reply_text(
            f"📝 *Summary*\n\n{summary}",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Summarizer unavailable. Try again!")
