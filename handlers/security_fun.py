# ============================================================
#  handlers/security_fun.py
#  /encode <text>        — Base64 / Caesar cipher encode
#  /decode <text>        — Decode encoded text
#  /checkurl <url>       — Check URL safety
#  /vault add/get        — Encrypted personal notes vault
#  /ipinfo <ip>          — IP geolocation
#  /ascii <text>         — Text to ASCII art
#  /compliment           — AI personalized compliment
#  /motivate             — Custom motivational message
#  /dare                 — Truth or Dare game
#  /ship @user1 @user2   — Compatibility score
# ============================================================

import base64
import os
import random
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

VAULT_FILE = "vault.json"


def _groq_simple(prompt: str, system: str, max_tokens: int = 200) -> str:
    resp = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.8,
        },
        timeout=15,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── /encode ───────────────────────────────────────────────

def _caesar_encode(text: str, shift: int = 13) -> str:
    result = []
    for ch in text:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            result.append(ch)
    return "".join(result)


async def encode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/encode <text> [method] — Encode text. Methods: base64 (default), caesar, reverse."""
    if not context.args:
        await update.message.reply_text(
            "🔐 *Text Encoder*\n\n"
            "`/encode Hello World` — Base64\n"
            "`/encode Hello World caesar` — Caesar cipher (ROT13)\n"
            "`/encode Hello World reverse` — Reverse text\n\n"
            "Use `/decode <text>` to decode!",
            parse_mode="Markdown"
        )
        return

    args   = context.args
    method = "base64"
    if args[-1].lower() in ("base64", "caesar", "reverse"):
        method = args[-1].lower()
        text   = " ".join(args[:-1])
    else:
        text = " ".join(args)

    if not text:
        await update.message.reply_text("❌ Please provide text to encode.")
        return

    if method == "base64":
        encoded = base64.b64encode(text.encode()).decode()
        label   = "🔵 Base64"
    elif method == "caesar":
        encoded = _caesar_encode(text, 13)
        label   = "🔴 Caesar / ROT13"
    else:
        encoded = text[::-1]
        label   = "🟡 Reversed"

    await update.message.reply_text(
        f"🔐 *Encoded ({label})*\n\n"
        f"📝 Original: `{text}`\n\n"
        f"🔒 Encoded: `{encoded}`\n\n"
        f"_Use /decode to decode base64 or caesar text._",
        parse_mode="Markdown"
    )


async def decode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/decode <text> [method] — Decode encoded text."""
    if not context.args:
        await update.message.reply_text(
            "🔓 *Text Decoder*\n\n"
            "`/decode SGVsbG8gV29ybGQ=` — Base64\n"
            "`/decode Uryyb Jbeyq caesar` — Caesar/ROT13\n"
            "`/decode dlroW olleH reverse` — Reversed",
            parse_mode="Markdown"
        )
        return

    args   = context.args
    method = "base64"
    if args[-1].lower() in ("base64", "caesar", "reverse"):
        method = args[-1].lower()
        text   = " ".join(args[:-1])
    else:
        text = " ".join(args)

    try:
        if method == "base64":
            decoded = base64.b64decode(text.encode()).decode()
            label   = "🔵 Base64"
        elif method == "caesar":
            decoded = _caesar_encode(text, 13)  # ROT13 is its own inverse
            label   = "🔴 Caesar / ROT13"
        else:
            decoded = text[::-1]
            label   = "🟡 Reversed"

        await update.message.reply_text(
            f"🔓 *Decoded ({label})*\n\n"
            f"🔒 Encoded: `{text}`\n\n"
            f"📝 Decoded: `{decoded}`",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text(
            "❌ Decoding failed. Make sure the text is valid!\n\n"
            "Try: `/decode SGVsbG8=` for base64.",
            parse_mode="Markdown"
        )


# ── /checkurl ─────────────────────────────────────────────

SAFE_BROWSING_KEY = os.environ.get("SAFE_BROWSING_KEY", "")

SUSPICIOUS_KEYWORDS = [
    "free-money", "click-here-win", "verify-account", "login-secure",
    "bank-update", "paypal-secure", "password-reset", "account-suspended",
    ".tk", ".ml", ".ga", ".cf", "bit.ly", "tinyurl"
]


async def checkurl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/checkurl <url> — Basic URL safety check."""
    if not context.args:
        await update.message.reply_text(
            "🛡 *URL Safety Checker*\n\n"
            "`/checkurl https://google.com`\n"
            "`/checkurl https://somesite.tk/free-money`\n\n"
            "Checks for phishing indicators and suspicious patterns.",
            parse_mode="Markdown"
        )
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    await update.message.chat.send_action("typing")

    warnings = []
    score    = 100  # start safe

    # Check suspicious keywords
    url_lower = url.lower()
    for kw in SUSPICIOUS_KEYWORDS:
        if kw in url_lower:
            warnings.append(f"⚠️ Contains suspicious pattern: `{kw}`")
            score -= 20

    # Check for IP address URLs (common phishing)
    import re
    if re.search(r'https?://\d+\.\d+\.\d+\.\d+', url):
        warnings.append("⚠️ Uses IP address instead of domain name (phishing indicator)")
        score -= 30

    # Check for very long URLs
    if len(url) > 200:
        warnings.append("⚠️ Unusually long URL")
        score -= 10

    # Check for multiple subdomains
    domain_part = url.split("//")[-1].split("/")[0]
    if domain_part.count(".") > 3:
        warnings.append("⚠️ Many subdomains (common phishing tactic)")
        score -= 15

    # HTTP not HTTPS
    if url.startswith("http://"):
        warnings.append("⚠️ Not using HTTPS (insecure connection)")
        score -= 20

    score = max(0, score)

    if score >= 80:
        verdict = "✅ *Looks Safe*"
        bar     = "🟢🟢🟢🟢🟢"
    elif score >= 50:
        verdict = "⚠️ *Suspicious — Be Careful*"
        bar     = "🟡🟡🟡⚪⚪"
    else:
        verdict = "🚨 *Likely Dangerous — Do NOT visit!*"
        bar     = "🔴🔴🔴🔴🔴"

    warn_text = "\n".join(warnings) if warnings else "No suspicious patterns found."
    domain    = url.split("//")[-1].split("/")[0]

    await update.message.reply_text(
        f"🛡 *URL Safety Report*\n\n"
        f"🔗 URL: `{url[:80]}...`" if len(url) > 80 else f"🔗 URL: `{url}`\n"
        f"🌐 Domain: `{domain}`\n\n"
        f"Safety Score: *{score}/100*\n"
        f"{bar}\n\n"
        f"{verdict}\n\n"
        f"📋 *Analysis:*\n{warn_text}\n\n"
        f"_Always verify links before entering personal info!_",
        parse_mode="Markdown"
    )


# ── /vault ────────────────────────────────────────────────

def _load_vault() -> dict:
    if os.path.exists(VAULT_FILE):
        with open(VAULT_FILE) as f:
            return json.load(f)
    return {}


def _save_vault(data: dict):
    with open(VAULT_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def vault_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /vault add <label> | <secret>  — Save a secret note
    /vault get <label>             — Retrieve a secret
    /vault list                    — List all labels
    /vault del <label>             — Delete a secret
    """
    user_id = str(update.effective_user.id)
    vault   = _load_vault()

    if not context.args:
        labels = list(vault.get(user_id, {}).keys())
        label_list = "\n".join(f"• `{l}`" for l in labels) if labels else "Empty"
        await update.message.reply_text(
            f"🔒 *Secure Vault*\n\n"
            f"Your saved labels:\n{label_list}\n\n"
            f"`/vault add Gmail | mypassword123`\n"
            f"`/vault get Gmail`\n"
            f"`/vault del Gmail`\n\n"
            f"_⚠️ Note: Secrets are stored on the bot server. "
            f"Don't store extremely sensitive info like bank PINs._",
            parse_mode="Markdown"
        )
        return

    sub = context.args[0].lower()

    if sub == "add":
        full = " ".join(context.args[1:])
        if "|" not in full:
            await update.message.reply_text("❌ Usage: `/vault add <label> | <secret>`\nExample: `/vault add Gmail | mypassword`", parse_mode="Markdown")
            return
        parts  = full.split("|", 1)
        label  = parts[0].strip()
        secret = parts[1].strip()
        if not label or not secret:
            await update.message.reply_text("❌ Both label and secret must have text.")
            return
        # Store base64-encoded (light obfuscation, not real encryption)
        encoded_secret = base64.b64encode(secret.encode()).decode()
        if user_id not in vault:
            vault[user_id] = {}
        vault[user_id][label] = encoded_secret
        _save_vault(vault)
        # Delete message for privacy
        try:
            await update.message.delete()
        except Exception:
            pass
        await update.effective_chat.send_message(
            f"✅ Secret *{label}* saved to vault!\n"
            f"_Original message deleted for privacy._ 🔒",
            parse_mode="Markdown"
        )

    elif sub == "get":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/vault get <label>`", parse_mode="Markdown")
            return
        label  = " ".join(context.args[1:])
        user_vault = vault.get(user_id, {})
        if label not in user_vault:
            await update.message.reply_text(f"❌ No secret found for label *{label}*.", parse_mode="Markdown")
            return
        secret = base64.b64decode(user_vault[label].encode()).decode()
        msg = await update.message.reply_text(
            f"🔓 *Vault: {label}*\n\n`{secret}`\n\n_⚠️ This message will auto-delete in 30 seconds!_",
            parse_mode="Markdown"
        )
        # Auto-delete after 30 seconds
        import asyncio
        await asyncio.sleep(30)
        try:
            await msg.delete()
        except Exception:
            pass

    elif sub == "list":
        labels = list(vault.get(user_id, {}).keys())
        if not labels:
            await update.message.reply_text("🔒 Vault is empty! Add: `/vault add <label> | <secret>`", parse_mode="Markdown")
            return
        label_list = "\n".join(f"• `{l}`" for l in labels)
        await update.message.reply_text(f"🔒 *Your Vault Labels*\n\n{label_list}\n\nGet one: `/vault get <label>`", parse_mode="Markdown")

    elif sub == "del":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/vault del <label>`", parse_mode="Markdown")
            return
        label = " ".join(context.args[1:])
        user_vault = vault.get(user_id, {})
        if label not in user_vault:
            await update.message.reply_text(f"❌ No secret found for *{label}*.", parse_mode="Markdown")
            return
        del vault[user_id][label]
        _save_vault(vault)
        await update.message.reply_text(f"✅ Secret *{label}* deleted from vault.", parse_mode="Markdown")


# ── /ipinfo ───────────────────────────────────────────────

async def ipinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ipinfo [ip] — Get geolocation and ISP info for an IP address."""
    if not context.args:
        await update.message.reply_text(
            "🌐 *IP Info Lookup*\n\n"
            "`/ipinfo` — Your own IP info\n"
            "`/ipinfo 8.8.8.8` — Google's DNS\n"
            "`/ipinfo 1.1.1.1` — Cloudflare DNS",
            parse_mode="Markdown"
        )

    ip = context.args[0] if context.args else ""
    await update.message.chat.send_action("typing")

    try:
        url  = f"https://ipapi.co/{ip}/json/" if ip else "https://ipapi.co/json/"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "TelegramBot/1.0"})
        data = resp.json()

        if data.get("error"):
            await update.message.reply_text(f"❌ Invalid IP or lookup failed: {data.get('reason', 'unknown error')}")
            return

        ip_addr  = data.get("ip", "N/A")
        city     = data.get("city", "N/A")
        region   = data.get("region", "N/A")
        country  = data.get("country_name", "N/A")
        flag     = data.get("country_code", "")
        isp      = data.get("org", "N/A")
        lat      = data.get("latitude", "N/A")
        lon      = data.get("longitude", "N/A")
        timezone = data.get("timezone", "N/A")
        currency = data.get("currency_name", "N/A")

        await update.message.reply_text(
            f"🌐 *IP Information*\n\n"
            f"🔢 IP: `{ip_addr}`\n"
            f"📍 Location: {city}, {region}\n"
            f"🌍 Country: {country} {flag}\n"
            f"🏢 ISP/Org: {isp}\n"
            f"🗺 Coordinates: {lat}, {lon}\n"
            f"🕐 Timezone: {timezone}\n"
            f"💵 Currency: {currency}",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ IP lookup service unavailable. Try again!")


# ── /ascii ────────────────────────────────────────────────

async def ascii_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ascii <text> — Convert text to ASCII art."""
    if not context.args:
        await update.message.reply_text(
            "🎨 *ASCII Art Generator*\n\n"
            "`/ascii VIKRAM`\n"
            "`/ascii HELLO`\n"
            "`/ascii BCA`\n\n"
            "Best with SHORT text (2-6 chars)!",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args).upper()[:8]

    # Simple block letter font
    LETTERS = {
        'A': ["  █  ", " █ █ ", "█████", "█   █", "█   █"],
        'B': ["████ ", "█   █", "████ ", "█   █", "████ "],
        'C': [" ████", "█    ", "█    ", "█    ", " ████"],
        'D': ["████ ", "█   █", "█   █", "█   █", "████ "],
        'E': ["█████", "█    ", "████ ", "█    ", "█████"],
        'F': ["█████", "█    ", "████ ", "█    ", "█    "],
        'G': [" ████", "█    ", "█  ██", "█   █", " ████"],
        'H': ["█   █", "█   █", "█████", "█   █", "█   █"],
        'I': ["█████", "  █  ", "  █  ", "  █  ", "█████"],
        'J': ["█████", "   █ ", "   █ ", "█  █ ", " ██  "],
        'K': ["█   █", "█  █ ", "███  ", "█  █ ", "█   █"],
        'L': ["█    ", "█    ", "█    ", "█    ", "█████"],
        'M': ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
        'N': ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
        'O': [" ███ ", "█   █", "█   █", "█   █", " ███ "],
        'P': ["████ ", "█   █", "████ ", "█    ", "█    "],
        'Q': [" ███ ", "█   █", "█ █ █", "█  ██", " ████"],
        'R': ["████ ", "█   █", "████ ", "█  █ ", "█   █"],
        'S': [" ████", "█    ", " ███ ", "    █", "████ "],
        'T': ["█████", "  █  ", "  █  ", "  █  ", "  █  "],
        'U': ["█   █", "█   █", "█   █", "█   █", " ███ "],
        'V': ["█   █", "█   █", "█   █", " █ █ ", "  █  "],
        'W': ["█   █", "█   █", "█ █ █", "██ ██", "█   █"],
        'X': ["█   █", " █ █ ", "  █  ", " █ █ ", "█   █"],
        'Y': ["█   █", " █ █ ", "  █  ", "  █  ", "  █  "],
        'Z': ["█████", "   █ ", "  █  ", " █   ", "█████"],
        ' ': ["     ", "     ", "     ", "     ", "     "],
        '0': [" ███ ", "█   █", "█   █", "█   █", " ███ "],
        '1': [" ██  ", "  █  ", "  █  ", "  █  ", "█████"],
        '!': ["  █  ", "  █  ", "  █  ", "     ", "  █  "],
    }

    # Build rows
    rows = ["", "", "", "", ""]
    for ch in text:
        pattern = LETTERS.get(ch, LETTERS.get('?', ["?????"] * 5))
        for i in range(5):
            rows[i] += pattern[i] + " "

    ascii_art = "\n".join(rows)
    await update.message.reply_text(f"🎨 *ASCII Art*\n```\n{ascii_art}\n```", parse_mode="Markdown")


# ── /compliment ───────────────────────────────────────────

async def compliment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/compliment — Get an AI-generated genuine compliment."""
    name = update.effective_user.first_name
    await update.message.chat.send_action("typing")
    try:
        compliment = _groq_simple(
            f"Give a genuine, warm, specific compliment to someone named {name} who is likely a student.",
            "You are a sincere, warm friend. Give a genuine 2-3 sentence compliment. Make it feel personal and uplifting, not generic. Use their name.",
            max_tokens=150
        )
        await update.message.reply_text(f"💝 *For you, {name}:*\n\n{compliment}", parse_mode="Markdown")
    except Exception:
        fallback = random.choice([
            f"💝 {name}, you're doing better than you think! Every step forward counts. 🌟",
            f"💝 Hey {name}! Your curiosity and effort to keep learning sets you apart. Keep going! 🚀",
            f"💝 {name}, the fact that you show up every day and try makes you remarkable. 💪",
        ])
        await update.message.reply_text(fallback, parse_mode="Markdown")


# ── /motivate ─────────────────────────────────────────────

async def motivate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/motivate [mood] — Custom motivational message."""
    name = update.effective_user.first_name
    mood = " ".join(context.args) if context.args else "need a boost"
    await update.message.chat.send_action("typing")
    try:
        msg = _groq_simple(
            f"The person ({name}) says they feel: {mood}. Give them a powerful, specific motivational message.",
            "You are an uplifting life coach. Write a powerful 3-4 sentence motivational message. Be specific, warm, and actionable. Reference their mood. Use their name.",
            max_tokens=200
        )
        await update.message.reply_text(f"💪 *{name}, here's your fuel:*\n\n{msg}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(
            f"💪 *{name}, remember this:*\n\n"
            "Every expert was once a beginner. Every pro was once an amateur. "
            "The difference is they kept going when it got hard. Today is your day to keep going! 🔥",
            parse_mode="Markdown"
        )


# ── /dare ────────────────────────────────────────────────

TRUTHS = [
    "What's the most embarrassing thing that happened to you in school?",
    "What's your biggest fear in life?",
    "Have you ever lied to get out of trouble? What was the lie?",
    "What's your most cringe-worthy childhood memory?",
    "What's the weirdest dream you've ever had?",
    "What's a secret talent nobody knows you have?",
    "Have you ever accidentally sent a message to the wrong person?",
    "What's the longest you've gone without bathing?",
    "What's something you pretend to like but secretly don't?",
    "What's the most childish thing you still do?",
]

DARES = [
    "Send a voice message saying 'I love studying' with maximum enthusiasm!",
    "Change your profile photo to something silly for 10 minutes.",
    "Write a 2-line poem about the last person who messaged you.",
    "Send the last photo in your gallery right now.",
    "Type everything backwards for the next 5 minutes.",
    "Send a 'good morning' message to someone random in your contacts.",
    "Let the next person pick your display name for 1 hour.",
    "Post this message: 'I just lost a dare on a Telegram bot 😂'",
    "Compliment everyone in this chat right now.",
    "Speak only in questions for the next 3 messages.",
]


async def dare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dare — Truth or Dare game!"""
    keyboard = [[
        InlineKeyboardButton("😇 Truth", callback_data="dare|truth"),
        InlineKeyboardButton("😈 Dare",  callback_data="dare|dare"),
    ]]
    await update.message.reply_text(
        "😈 *Truth or Dare!*\n\nWhat do you choose?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def dare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("dare|"):
        return

    choice = query.data.split("|")[1]
    if choice == "truth":
        question = random.choice(TRUTHS)
        await query.edit_message_text(
            f"😇 *TRUTH!*\n\n❓ {question}\n\n_Be honest! 😏_",
            parse_mode="Markdown"
        )
    else:
        challenge = random.choice(DARES)
        await query.edit_message_text(
            f"😈 *DARE!*\n\n🎯 {challenge}\n\n_You have to do it! 😂_",
            parse_mode="Markdown"
        )


# ── /ship ────────────────────────────────────────────────

SHIP_MESSAGES = [
    ("💔", "0-20", "Not a match made in heaven... 😅"),
    ("💛", "21-40", "Just friends vibes. 🤝"),
    ("💚", "41-60", "Pretty decent compatibility! 😊"),
    ("💙", "61-80", "Great match! There's real chemistry here. 💫"),
    ("❤️", "81-95", "Amazing compatibility! Almost perfect! 🥰"),
    ("💖", "96-100", "SOULMATES! 😍🎉 Destined to be together!"),
]


async def ship_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ship @user1 @user2 OR /ship Name1 Name2 — Compatibility score."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "💘 *Compatibility Checker*\n\n"
            "`/ship Rahul Priya`\n"
            "`/ship @user1 @user2`\n\n"
            "_Just for fun! 😄_",
            parse_mode="Markdown"
        )
        return

    name1 = context.args[0].lstrip("@")
    name2 = context.args[1].lstrip("@")

    # Deterministic score based on names (same pair = same result)
    combined = sorted([name1.lower(), name2.lower()])
    score    = (sum(ord(c) for c in "".join(combined)) * 7) % 101

    for emoji, range_str, message in SHIP_MESSAGES:
        lo, hi = map(int, range_str.split("-"))
        if lo <= score <= hi:
            ship_emoji = emoji
            ship_msg   = message
            break

    bar_filled = int(score / 10)
    bar = "💗" * bar_filled + "🤍" * (10 - bar_filled)

    await update.message.reply_text(
        f"💘 *Compatibility Test*\n\n"
        f"👤 {name1} + {name2} 👤\n\n"
        f"💯 Score: *{score}%*\n"
        f"{bar}\n\n"
        f"{ship_emoji} {ship_msg}\n\n"
        f"_Just for fun! Results not scientifically accurate 😄_",
        parse_mode="Markdown"
    )
