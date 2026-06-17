# ============================================================
#  handlers/jokes.py
#  /joke command — fetches a random programming joke
# ============================================================

import requests
from telegram import Update
from telegram.ext import ContextTypes


async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch a random programming joke from JokeAPI."""
    try:
        # blacklistFlags=nsfw,explicit keeps jokes clean
        url = "https://v2.jokeapi.dev/joke/Programming,Misc?blacklistFlags=nsfw,explicit"
        data = requests.get(url, timeout=5).json()

        if data.get("type") == "twopart":
            # Two-part joke: setup + punchline
            joke = f"😂 *{data['setup']}*\n\n_{data['delivery']}_"
        else:
            joke = f"😂 {data.get('joke', 'No joke found.')}"

        await update.message.reply_text(joke, parse_mode="Markdown")

    except Exception:
        # Fallback joke in case the API is down
        await update.message.reply_text(
            "😂 Why do programmers prefer dark mode?\n\n"
            "_Because light attracts bugs!_",
            parse_mode="Markdown"
        )
