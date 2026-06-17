# ============================================================
#  handlers/social.py
#  /contact — Vikram's social links & portfolio
# ============================================================

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ── Your social links ─────────────────────────────────────
SOCIAL_LINKS = {
    "instagram": "https://instagram.com/vikram14052006",
    "linkedin":  "https://www.linkedin.com/in/vikram14052006",
    "github":    "https://github.com/Babamosie333",
    "youtube":   "https://www.youtube.com/@DevBabaMosie",
    "portfolio": "https://vikramsingh.itsfolio.tech",
}


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/contact — Show all of Vikram's social links as tap buttons."""

    text = (
        "👨‍💻 *Vikram Singh*\n"
        "BCA Student | Developer\n\n"
        "Connect with me on any platform below 👇"
    )

    # Each social link becomes a tap-to-open inline button
    keyboard = [
        [InlineKeyboardButton("📸 Instagram",  url=SOCIAL_LINKS["instagram"])],
        [InlineKeyboardButton("💼 LinkedIn",   url=SOCIAL_LINKS["linkedin"])],
        [InlineKeyboardButton("🐙 GitHub",     url=SOCIAL_LINKS["github"])],
        [InlineKeyboardButton("▶️ YouTube",    url=SOCIAL_LINKS["youtube"])],
        [InlineKeyboardButton("🌐 Portfolio",  url=SOCIAL_LINKS["portfolio"])],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
