# ============================================================
#  handlers/games.py
#  /hangman — Word guessing game
#  /rps <rock|paper|scissors> — Rock Paper Scissors
#  /8ball <question> — Magic 8 ball
#  /wouldyourather — Random WYR question
#  /story — Collaborative AI story
# ============================================================

import random
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── Hangman word list ─────────────────────────────────────
HANGMAN_WORDS = [
    "python", "javascript", "database", "algorithm", "recursion",
    "compiler", "variable", "function", "boolean", "integer",
    "keyboard", "monitor", "network", "software", "hardware",
    "programming", "developer", "framework", "repository", "terminal",
    "bandwidth", "firewall", "protocol", "encryption", "debugging",
    "inheritance", "polymorphism", "abstraction", "encapsulation",
    "telegram", "internet", "computer", "processor", "memory",
]

HANGMAN_STAGES = [
    "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
]

# Active hangman games per user: { user_id: { word, guessed: [], wrong: [] } }
hangman_games: dict[str, dict] = {}


def _hangman_display(game: dict) -> str:
    word    = game["word"]
    guessed = game["guessed"]   # list
    wrong   = game["wrong"]     # list
    stage   = HANGMAN_STAGES[min(len(wrong), 6)]
    display = " ".join(c if c in guessed else "_" for c in word)
    wrong_str = " ".join(sorted(wrong)) if wrong else "None yet"
    lives   = 6 - len(wrong)
    return (
        f"{stage}\n\n"
        f"Word: `{display}`\n"
        f"❌ Wrong: `{wrong_str}`\n"
        f"Lives: {'❤️' * lives}{'🖤' * len(wrong)}\n\n"
        f"*Send a single letter to guess!*"
    )


async def hangman_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/hangman — Start a new hangman game."""
    user_id = str(update.effective_user.id)
    word    = random.choice(HANGMAN_WORDS)
    hangman_games[user_id] = {"word": word, "guessed": [], "wrong": []}
    game = hangman_games[user_id]
    await update.message.reply_text(
        f"🎯 *Hangman Game Started!*\n\n"
        f"{_hangman_display(game)}\n\n"
        f"_The word has {len(word)} letters. Good luck!_\n"
        f"Use /hangman anytime to restart.",
        parse_mode="Markdown"
    )


async def hangman_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle single-letter guesses for hangman.
    Returns True if the message was consumed by hangman, False otherwise.
    """
    user_id = str(update.effective_user.id)
    if user_id not in hangman_games:
        return False

    text   = update.message.text.strip().lower()
    # Only consume single alphabetic characters
    if len(text) != 1 or not text.isalpha():
        return False

    game    = hangman_games[user_id]
    word    = game["word"]
    guessed = game["guessed"]
    wrong   = game["wrong"]
    letter  = text

    # Already guessed?
    if letter in guessed or letter in wrong:
        await update.message.reply_text(
            f"⚠️ You already guessed `{letter}`! Try a different letter.\n\n"
            f"{_hangman_display(game)}",
            parse_mode="Markdown"
        )
        return True

    if letter in word:
        guessed.append(letter)
        # Check win — all letters revealed
        if all(c in guessed for c in word):
            del hangman_games[user_id]
            await update.message.reply_text(
                f"🎉 *You won!*\n\nThe word was: *`{word}`* 🎊\n\nPlay again? /hangman",
                parse_mode="Markdown"
            )
            return True
        await update.message.reply_text(
            f"✅ Yes! `{letter}` is in the word!\n\n{_hangman_display(game)}",
            parse_mode="Markdown"
        )
    else:
        wrong.append(letter)
        if len(wrong) >= 6:
            del hangman_games[user_id]
            await update.message.reply_text(
                f"💀 *Game Over!*\n\nThe word was: *`{word}`*\n\nTry again? /hangman",
                parse_mode="Markdown"
            )
            return True
        await update.message.reply_text(
            f"❌ Nope! `{letter}` is not in the word.\n\n{_hangman_display(game)}",
            parse_mode="Markdown"
        )

    return True


# ── Rock Paper Scissors ───────────────────────────────────

RPS_CHOICES = ["rock", "paper", "scissors"]
RPS_EMOJI   = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
RPS_BEATS   = {"rock": "scissors", "scissors": "paper", "paper": "rock"}


async def rps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/rps <rock|paper|scissors> — Play RPS against the bot."""
    if not context.args:
        keyboard = [[
            InlineKeyboardButton("🪨 Rock",     callback_data="rps|rock"),
            InlineKeyboardButton("📄 Paper",    callback_data="rps|paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="rps|scissors"),
        ]]
        await update.message.reply_text(
            "🎮 *Rock Paper Scissors!*\n\nPick your move:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    user_choice = context.args[0].lower()
    if user_choice not in RPS_CHOICES:
        await update.message.reply_text("❌ Choose: rock, paper, or scissors")
        return

    await _rps_result(update, user_choice, reply_func=update.message.reply_text)


async def rps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("rps|"):
        return
    user_choice = query.data.split("|")[1]
    bot_choice  = random.choice(RPS_CHOICES)
    ue = RPS_EMOJI[user_choice]
    be = RPS_EMOJI[bot_choice]

    if user_choice == bot_choice:
        result = "🤝 *It's a tie!*"
    elif RPS_BEATS[user_choice] == bot_choice:
        result = "🎉 *You win!*"
    else:
        result = "🤖 *Bot wins!*"

    await query.edit_message_text(
        f"🎮 *Rock Paper Scissors*\n\n"
        f"You: {ue} {user_choice.capitalize()}\n"
        f"Bot: {be} {bot_choice.capitalize()}\n\n"
        f"{result}",
        parse_mode="Markdown"
    )


async def _rps_result(update, user_choice, reply_func):
    bot_choice = random.choice(RPS_CHOICES)
    ue = RPS_EMOJI[user_choice]
    be = RPS_EMOJI[bot_choice]
    if user_choice == bot_choice:
        result = "🤝 *It's a tie!*"
    elif RPS_BEATS[user_choice] == bot_choice:
        result = "🎉 *You win!*"
    else:
        result = "🤖 *Bot wins!*"
    await reply_func(
        f"🎮 *Rock Paper Scissors*\n\n"
        f"You: {ue} {user_choice.capitalize()}\n"
        f"Bot: {be} {bot_choice.capitalize()}\n\n"
        f"{result}",
        parse_mode="Markdown"
    )


# ── Magic 8 Ball ──────────────────────────────────────────

EIGHT_BALL_ANSWERS = [
    "✅ It is certain.", "✅ It is decidedly so.", "✅ Without a doubt.",
    "✅ Yes, definitely!", "✅ You may rely on it.", "✅ As I see it, yes.",
    "✅ Most likely.", "✅ Outlook good.", "✅ Yes!", "✅ Signs point to yes.",
    "🤔 Reply hazy, try again.", "🤔 Ask again later.",
    "🤔 Better not tell you now.", "🤔 Cannot predict now.",
    "🤔 Concentrate and ask again.",
    "❌ Don't count on it.", "❌ My reply is no.",
    "❌ My sources say no.", "❌ Outlook not so good.", "❌ Very doubtful.",
]


async def eightball_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/8ball <question> — Ask the magic 8 ball."""
    if not context.args:
        await update.message.reply_text(
            "🎱 *Ask the Magic 8 Ball!*\n\n"
            "Example: `/8ball Will I pass my exams?`",
            parse_mode="Markdown"
        )
        return

    question = " ".join(context.args)
    answer   = random.choice(EIGHT_BALL_ANSWERS)
    await update.message.reply_text(
        f"🎱 *Magic 8 Ball*\n\n"
        f"❓ _{question}_\n\n"
        f"🎱 {answer}",
        parse_mode="Markdown"
    )


# ── Would You Rather ─────────────────────────────────────

WYR_QUESTIONS = [
    ("Have the ability to fly ✈️", "Be invisible 👻"),
    ("Live without music 🎵", "Live without internet 🌐"),
    ("Be a top YouTuber 🎥", "Be a top software engineer 💻"),
    ("Know all languages 🌍", "Know how to play all instruments 🎸"),
    ("Have 10 true friends 👫", "Have 1000 fake followers 📱"),
    ("Never sleep again 😴", "Never eat your favourite food 🍕"),
    ("Be super smart 🧠", "Be super attractive 💅"),
    ("Live in 1800s 🏰", "Live in 2200s 🚀"),
    ("Speak to animals 🐶", "Speak all human languages 🌏"),
    ("Have unlimited money 💰", "Unlimited time ⏰"),
    ("Code in one language forever 💻", "Switch language every 6 months 🔄"),
    ("Debug others' code 🐛", "Write docs for your own code 📝"),
    ("Be a startup founder with risk 🚀", "Work at a big tech company safely 🏢"),
    ("Learn everything fast but forget quickly 📚", "Learn slowly but remember forever 🧠"),
    ("Have 1 hour extra every day ⏰", "Earn ₹5000 extra every month 💵"),
]


async def wouldyourather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/wouldyourather — Random WYR question."""
    opt_a, opt_b = random.choice(WYR_QUESTIONS)
    keyboard = [[
        InlineKeyboardButton(f"🅰️ {opt_a[:30]}", callback_data="wyr|A"),
        InlineKeyboardButton(f"🅱️ {opt_b[:30]}", callback_data="wyr|B"),
    ]]
    await update.message.reply_text(
        f"🤔 *Would You Rather...*\n\n"
        f"🅰️ {opt_a}\n\n*OR*\n\n🅱️ {opt_b}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def wyr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("wyr|"):
        return
    choice = query.data.split("|")[1]
    emoji  = "🅰️" if choice == "A" else "🅱️"
    await query.edit_message_text(
        query.message.text + f"\n\n{emoji} *You chose option {choice}!*\n\nPlay again? /wouldyourather",
        parse_mode="Markdown"
    )


# ── Collaborative AI Story ────────────────────────────────

# story_data: { user_id: [lines...] }
story_data: dict[str, list] = {}


async def story_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/story — Start or continue a collaborative AI story."""
    user_id = str(update.effective_user.id)

    if not context.args:
        # Start new story
        story_data[user_id] = []
        await update.message.reply_text(
            "📖 *Collaborative Story!*\n\n"
            "Start the story by sending your first line!\n"
            "I'll continue it, then you add more.\n\n"
            "_Type your opening line now..._\n"
            "Use /storyclear to start fresh.",
            parse_mode="Markdown"
        )
        return

    user_line = " ".join(context.args)
    if user_id not in story_data:
        story_data[user_id] = []

    story_data[user_id].append(f"User: {user_line}")

    # Build story so far for context
    story_so_far = "\n".join(story_data[user_id])

    await update.message.chat.send_action("typing")

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content":
                        "You are a creative story writer. Continue the collaborative story "
                        "with exactly 2-3 sentences. Keep it engaging, age-appropriate, and "
                        "leave it on a cliffhanger so the user wants to continue. "
                        "Only write your continuation — no meta-commentary."},
                    {"role": "user", "content": f"Story so far:\n{story_so_far}\n\nContinue the story:"}
                ],
                "max_tokens": 150,
                "temperature": 0.9,
            },
            timeout=15
        )
        ai_line = resp.json()["choices"][0]["message"]["content"].strip()
        story_data[user_id].append(f"Bot: {ai_line}")

        await update.message.reply_text(
            f"📖 *Story continues...*\n\n_{ai_line}_\n\n"
            f"Your turn! Use `/story <your next line>`",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Story AI unavailable. Try again!")


async def storyclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/storyclear — Clear current story and start fresh."""
    user_id = str(update.effective_user.id)
    story_data.pop(user_id, None)
    await update.message.reply_text("🗑 Story cleared! Start a new one with /story")
