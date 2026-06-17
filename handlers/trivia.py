# ============================================================
#  handlers/trivia.py
#  /trivia — Interactive trivia game with tap-to-answer buttons
#
#  Uses Telegram's InlineKeyboardButton so users tap an option
#  instead of typing — much better UX!
# ============================================================

import requests
import html                                            # To decode HTML entities from the API
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random


def fetch_question() -> dict | None:
    """Fetch one trivia question from the Open Trivia DB (free, no key needed)."""
    try:
        url = "https://opentdb.com/api.php?amount=1&type=multiple"
        data = requests.get(url, timeout=6).json()
        return data["results"][0]
    except Exception:
        return None


async def trivia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/trivia — Fetch a question and show answer options as buttons."""
    await update.message.reply_text("🎮 Loading your trivia question…")

    question_data = fetch_question()

    if not question_data:
        await update.message.reply_text("❌ Couldn't load a question. Try again!")
        return

    # Decode HTML entities (the API returns things like &amp; &quot;)
    question    = html.unescape(question_data["question"])
    correct     = html.unescape(question_data["correct_answer"])
    wrong       = [html.unescape(a) for a in question_data["incorrect_answers"]]
    category    = html.unescape(question_data["category"])
    difficulty  = question_data["difficulty"].capitalize()

    # Shuffle correct answer among the wrong ones
    all_answers = wrong + [correct]
    random.shuffle(all_answers)

    # Build inline keyboard — each answer is a button
    # callback_data carries a small string we parse when the button is tapped
    keyboard = []
    for i, answer in enumerate(all_answers):
        # Format: "trivia|<is_correct>|<answer_text_short>"
        is_correct = "1" if answer == correct else "0"
        keyboard.append([
            InlineKeyboardButton(
                text=answer,
                callback_data=f"trivia|{is_correct}|{answer[:30]}"  # max 64 chars allowed
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"🎮 *Trivia Time!*\n\n"
        f"📚 Category: {category}\n"
        f"⚡ Difficulty: {difficulty}\n\n"
        f"❓ *{question}*"
    )
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")


async def trivia_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles when the user taps one of the answer buttons."""
    query = update.callback_query
    await query.answer()                               # Acknowledge the button tap (removes loading spinner)

    # Only handle trivia callbacks (other buttons in the bot use different prefixes)
    if not query.data.startswith("trivia|"):
        return

    parts      = query.data.split("|")
    is_correct = parts[1]                              # "1" = correct, "0" = wrong
    chosen     = parts[2]                              # The answer text they tapped

    if is_correct == "1":
        response = (
            f"✅ *Correct!* Well done!\n\n"
            f"You chose: _{chosen}_\n\n"
            "Play again? /trivia"
        )
    else:
        response = (
            f"❌ *Wrong!* Better luck next time.\n\n"
            f"You chose: _{chosen}_\n\n"
            "Try again? /trivia"
        )

    # Edit the original message to show the result (cleaner than sending a new message)
    await query.edit_message_text(response, parse_mode="Markdown")
