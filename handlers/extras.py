# ============================================================
#  handlers/extras.py
#  /define, /quote, /fact — Dictionary, quotes, fun facts
# ============================================================

import requests
import random
from telegram import Update
from telegram.ext import ContextTypes

# ── Offline motivational quotes list ─────────────────────
QUOTES = [
    ("The best way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("Don't let yesterday take up too much of today.", "Will Rogers"),
    ("You learn more from failure than from success.", "Unknown"),
    ("It's not whether you get knocked down, it's whether you get up.", "Vince Lombardi"),
    ("If you are working on something exciting, it keeps you motivated.", "Steve Jobs"),
    ("Success is not final, failure is not fatal: keep going.", "Winston Churchill"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Code is like humor. When you have to explain it, it's bad.", "Cory House"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Experience is the name everyone gives to their mistakes.", "Oscar Wilde"),
    ("In order to be irreplaceable, one must always be different.", "Coco Chanel"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Don't watch the clock; do what it does — keep going.", "Sam Levenson"),
    ("Your time is limited, so don't waste it living someone else's life.", "Steve Jobs"),
]

# ── Offline fun facts list ────────────────────────────────
FACTS = [
    "🧠 The human brain can store approximately 2.5 petabytes of data!",
    "💻 The first computer bug was an actual real bug — a moth found in a Harvard computer in 1947.",
    "🌍 More people have mobile phones than toilets in the world.",
    "🐙 Octopuses have three hearts and blue blood.",
    "🍯 Honey never expires — archaeologists found 3000-year-old honey in Egyptian tombs, still edible!",
    "🦈 Sharks are older than trees — they've existed for over 400 million years.",
    "🌙 A day on Venus is longer than a year on Venus.",
    "🐧 Penguins propose to their partners with pebbles.",
    "⚡ Lightning strikes the Earth about 100 times every second.",
    "🦋 Butterflies taste with their feet.",
    "🎵 Music was the first thing ever downloaded illegally on the internet.",
    "🔢 The word 'algorithm' comes from the name of Persian mathematician Al-Khwarizmi.",
    "🌐 The first website ever is still online — info.cern.ch",
    "🐘 Elephants are the only animals that can't jump.",
    "🍕 The first pizza was made in Naples, Italy in the 18th century.",
    "💡 The average person spends 6 months of their lifetime waiting for red lights.",
    "🚀 Space is completely silent — sound can't travel in a vacuum.",
    "🦁 A group of flamingos is called a 'flamboyance'.",
    "🧊 Hot water freezes faster than cold water — this is called the Mpemba effect.",
    "🐍 Python programming language is named after Monty Python, not the snake!",
]


async def define_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/define <word> — Get the dictionary definition of a word."""
    if not context.args:
        await update.message.reply_text(
            "Please provide a word to define.\n"
            "Example: `/define recursion`",
            parse_mode="Markdown"
        )
        return

    word = context.args[0].lower().strip()
    await update.message.chat.send_action("typing")

    try:
        # Free Dictionary API — no key needed
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        resp = requests.get(url, timeout=6)

        if resp.status_code == 404:
            await update.message.reply_text(
                f"❌ No definition found for *{word}*.\n"
                "Check the spelling and try again.",
                parse_mode="Markdown"
            )
            return

        data = resp.json()[0]
        word_text  = data.get("word", word).capitalize()
        phonetic   = data.get("phonetic", "")
        meanings   = data.get("meanings", [])

        lines = [f"📖 *{word_text}*  {phonetic}\n"]

        # Show up to 3 meanings with up to 2 definitions each
        for meaning in meanings[:3]:
            part = meaning.get("partOfSpeech", "")      # noun, verb, adjective...
            lines.append(f"_{part}_")
            defs = meaning.get("definitions", [])
            for i, d in enumerate(defs[:2], 1):
                definition = d.get("definition", "")
                example    = d.get("example", "")
                lines.append(f"  {i}. {definition}")
                if example:
                    lines.append(f'     _e.g. "{example}"_')
            lines.append("")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("❌ Dictionary service unavailable. Try again later.")


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/quote — Send a random motivational quote."""
    quote, author = random.choice(QUOTES)
    text = f"💬 *\"{quote}\"*\n\n— _{author}_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def fact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/fact — Send a random fun fact."""
    fact = random.choice(FACTS)
    await update.message.reply_text(f"🤯 *Fun Fact!*\n\n{fact}", parse_mode="Markdown")
