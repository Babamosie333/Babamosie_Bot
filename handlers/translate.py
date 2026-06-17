# ============================================================
#  handlers/translate.py
#  /translate <text> to <language>
#  Uses MyMemory free API — no key needed, 1000 req/day free
#  Examples:
#    /translate Hello to Hindi
#    /translate Namaste to English
#    /translate Good morning to Spanish
# ============================================================

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

# Language name → code mapping (most common ones)
LANG_CODES = {
    "hindi": "hi", "english": "en", "spanish": "es",
    "french": "fr", "german": "de", "italian": "it",
    "portuguese": "pt", "russian": "ru", "japanese": "ja",
    "chinese": "zh", "korean": "ko", "arabic": "ar",
    "bengali": "bn", "tamil": "ta", "telugu": "te",
    "marathi": "mr", "gujarati": "gu", "punjabi": "pa",
    "urdu": "ur", "kannada": "kn", "malayalam": "ml",
    "dutch": "nl", "swedish": "sv", "turkish": "tr",
    "polish": "pl", "vietnamese": "vi", "thai": "th",
}


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /translate <text> to <language>
    OR /translate <text>  ← uses language saved by /setlang
    Auto-detects source language.
    """
    user_id = str(update.effective_user.id)
    saved_lang = _get_user_pref(user_id, "lang", None)

    if not context.args:
        hint = f"\n\n💡 Your saved language: *{saved_lang.capitalize()}* (set via /setlang)" if saved_lang else ""
        await update.message.reply_text(
            "🌐 *How to use /translate:*\n\n"
            "`/translate Hello to Hindi`\n"
            "`/translate Namaste to English`\n"
            "`/translate Good morning to Spanish`\n"
            "`/translate Hello` ← uses your /setlang language\n\n"
            "🗣 Supported: Hindi, English, Spanish, French, German, "
            "Japanese, Chinese, Korean, Arabic, Bengali, Tamil, Telugu, "
            "Marathi, Urdu, and 20+ more!" + hint,
            parse_mode="Markdown"
        )
        return

    full_text  = " ".join(context.args)
    lower_text = full_text.lower()
    split_idx  = lower_text.rfind(" to ")

    # If user typed "to <lang>" at the end, extract it; otherwise use saved lang
    if split_idx != -1:
        source_text = full_text[:split_idx].strip()
        target_lang = full_text[split_idx + 4:].strip().lower()
    else:
        # No "to <lang>" in command — use saved preference
        source_text = full_text.strip()
        if saved_lang:
            target_lang = saved_lang
        else:
            await update.message.reply_text(
                "❌ Please specify a language or set one with /setlang\n\n"
                "Example: `/translate Hello to Hindi`\n"
                "Or: `/setlang Hindi` then `/translate Hello`",
                parse_mode="Markdown"
            )
            return

    if not source_text:
        await update.message.reply_text("❌ Please provide text to translate.")
        return

    # Get language code
    lang_code = LANG_CODES.get(target_lang)
    if not lang_code:
        # Try if they typed a code directly like "hi" or "fr"
        if target_lang in LANG_CODES.values():
            lang_code = target_lang
        else:
            supported = ", ".join(sorted(LANG_CODES.keys()))
            await update.message.reply_text(
                f"❌ Unknown language: *{target_lang}*\n\n"
                f"Supported languages:\n`{supported}`",
                parse_mode="Markdown"
            )
            return

    await update.message.chat.send_action("typing")

    try:
        # MyMemory free translation API
        # Note: "auto" is NOT a valid source — use "en" as default source
        # For non-English source text, detect by trying en first
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q":        source_text,
            "langpair": f"en|{lang_code}",   # assume English source
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        status = data.get("responseStatus")

        # If same-language or error, try without specifying source (let server guess)
        if status != 200 or data["responseData"]["translatedText"].strip().lower() == source_text.strip().lower():
            params["langpair"] = f"|{lang_code}"
            resp = requests.get(url, params=params, timeout=8)
            data = resp.json()
            status = data.get("responseStatus")

        if status != 200:
            await update.message.reply_text(
                f"❌ Translation failed (status {status}). Try again later."
            )
            return

        translated     = data["responseData"]["translatedText"]
        target_display = target_lang.capitalize()

        await update.message.reply_text(
            f"🌐 *Translation*\n\n"
            f"📝 Original:\n_{source_text}_\n\n"
            f"✅ {target_display}:\n*{translated}*",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text("❌ Translation service unavailable. Try again later.")
