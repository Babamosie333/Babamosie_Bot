from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    # Handle deep links: /start trivia, /start hangman etc
    if context.args:
        deeplink = context.args[0].lower()
        deep_map = {
            "trivia": "/trivia", "hangman": "/hangman", "menu": "/menu",
            "help": "/help", "ai": "/ai", "quiz": "/quiz",
        }
        if deeplink in deep_map:
            await update.message.reply_text(
                f"👋 Hey *{name}*! Starting {deep_map[deeplink]} for you...",
                parse_mode="Markdown"
            )

    await update.message.reply_text(
        f"👋 Hey *{name}*! I'm *Vikram's Bot v8.0* 🤖\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🧠 *AI* — /ai · /ask · /explain · /code · /memory\n"
        "         /rewrite · /grammar · /summarizeurl\n\n"
        "🎮 *Games* — /trivia · /hangman · /rps · /8ball\n"
        "            /dare · /ship · /mathquiz · /typetest\n\n"
        "📚 *Study* — /syllabus · /pyq · /studyplan\n"
        "            /doubt · /codereview · /flashcard\n\n"
        "📊 *Finance* — /crypto · /stock · /currency · /emi\n\n"
        "⚡ *Productivity* — /todo · /pomodoro · /countdown\n\n"
        "🔔 *Automation* — /birthday · /habit · /journal\n\n"
        "🛠 *Tools* — /weather · /translate · /qr · /shorten\n\n"
        "🔐 *Security* — /vault · /encode · /checkurl\n\n"
        "👥 *Groups* — /warn · /mute · /rules · /antiflood\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📋 /menu — Interactive button menu\n"
        "📖 /help — Full command list\n"
        "🏓 /ping — Check bot status\n"
        "💬 /feedback — Send feedback to Vikram",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    part1 = (
        "📋 *All Commands — Vikram's Bot v8.0*\n\n"
        "━━━━ 🧠 AI & Chat ━━━━\n"
        "/ai · /ask — Ask AI anything\n"
        "/imagine — AI scene description 🎨\n"
        "/explain `[for 5/teen/expert/bca]`\n"
        "/code — Generate code 💻\n"
        "/quiz — AI custom MCQ\n"
        "/rewrite `<style> | <text>`\n"
        "/grammar — Fix grammar + explain\n"
        "/summarizeurl — Summarize any URL 🔗\n"
        "/memory · /memory clear\n"
        "/persona · /resetpersona\n"
        "/roast · /debate · /summarize · /story\n\n"
        "━━━━ 📚 Student Tools ━━━━\n"
        "/syllabus `<course> <semester>`\n"
        "/pyq `<subject>` — Previous year questions\n"
        "/studyplan `<topic> <days>`\n"
        "/doubt `<question>` — Detailed explanation\n"
        "/codereview — Review code (reply to code)\n"
        "/flashcard add/quiz/list/clear\n"
        "/mcq · /essay · /formula · /dictionary\n"
        "/define · /tip · /word\n\n"
        "━━━━ 🎮 Games & Fun ━━━━\n"
        "/trivia · /hangman · /rps · /8ball\n"
        "/wouldyourather · /dare · /ship\n"
        "/compliment · /motivate · /story\n"
        "/mathquiz · /typetest\n\n"
        "━━━━ 📊 Finance ━━━━\n"
        "/crypto · /currency · /stock\n"
        "/pricealert · /emi · /bmi · /gpa\n\n"
        "━━━━ ⚡ Productivity ━━━━\n"
        "/todo add/list/done/del/clear\n"
        "/calc · /countdown · /pomodoro\n"
        "/remind · /agedays · /timezone\n"
    )
    part2 = (
        "━━━━ 🛠 Utilities ━━━━\n"
        "/weather · /forecast · /news · /topicnews\n"
        "/time · /timezone · /translate\n"
        "/horoscope · /shorten · /lyrics\n"
        "/joke · /quote · /fact · /random\n"
        "/youtube · /spotify\n\n"
        "━━━━ 🎬 Media ━━━━\n"
        "/meme · /movie · /anime\n"
        "/youtube · /spotify\n\n"
        "━━━━ 🔔 Automation ━━━━\n"
        "/subscribe news `<keyword>`\n"
        "/unsubscribe · /pricealert\n"
        "/birthday add/list/del\n"
        "/habit add/done/streak/del\n"
        "/journal · /journal history\n\n"
        "━━━━ 🔐 Security & Privacy ━━━━\n"
        "/encode · /decode · /vault\n"
        "/checkurl · /ipinfo · /ascii\n\n"
        "━━━━ 🔧 Tools ━━━━\n"
        "/password · /qr · /poll · /note\n"
        "/notes · /clearnotes\n\n"
        "━━━━ 👥 Group Admin ━━━━\n"
        "/welcome · /warn · /warnings\n"
        "/mute · /unmute · /antiflood\n"
        "/report · /rules · /tagall\n\n"
        "━━━━ ⚙️ Personalize ━━━━\n"
        "/setcity · /setlang · /theme\n"
        "/mystats · /leaderboard · /memory\n\n"
        "━━━━ 🌐 Extras ━━━━\n"
        "/github `<username>` — GitHub profile\n"
        "/inline — How to use inline mode\n"
        "/ping · /feedback · /contact\n\n"
        "━━━━ 📊 Admin Only ━━━━\n"
        "/stats · /users · /broadcast\n"
        "/log · /viewfeedback · /testbrief\n\n"
        "_Use /menu for interactive buttons!_ 🎛"
    )
    await update.message.reply_text(part1, parse_mode="Markdown")
    await update.message.reply_text(part2, parse_mode="Markdown")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Vikram's Advanced Telegram Bot v8.0*\n\n"
        "🛠 *Stack:*\n"
        "• Python 3.12 + python-telegram-bot 21.x\n"
        "• Groq API + LLaMA 3.3 70B (free AI)\n"
        "• APScheduler (cron jobs)\n"
        "• File-based logging\n"
        "• 20 handler modules\n\n"
        "📡 *Free APIs:*\n"
        "• CoinGecko — Crypto · Yahoo Finance — Stocks\n"
        "• ExchangeRate API — Currency\n"
        "• OMDB — Movies · Jikan — Anime\n"
        "• meme-api.com — Memes · wttr.in — Weather\n"
        "• GitHub API — Developer profiles\n"
        "• Open Trivia DB · Dictionary API\n"
        "• MyMemory — Translation\n"
        "• QRServer · TinyURL · ipapi.co\n\n"
        "✨ *110+ commands | 20 modules*\n"
        "🧠 AI Memory | ⚡ Inline Mode | 📋 /menu\n\n"
        "👨‍💻 Made by *Vikram Singh*\n"
        "🎓 BCA Student | Developer\n"
        "🔗 /contact · /feedback",
        parse_mode="Markdown"
    )
