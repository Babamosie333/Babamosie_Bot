# ============================================================
#  handlers/evolution.py  — Bot Evolution Pack
#
#  /forecast <city>      — 3-day weather forecast
#  /news <topic>         — Topic-specific news search
#  /dictionary <word>    — Enhanced: meaning + synonyms + Hindi
#  /tip <topic>          — Quick pro tip on any topic
#  /random               — Random useful thing (fact/quote/joke/tip)
#  /word                 — Word of the day
#  /mathquiz             — Quick mental math quiz
#  /typetest             — Typing speed test
#  /colorfact            — Random colour psychology fact
#  /thisorthat           — This or That rapid-fire game
#  /agedays <DD-MM-YYYY> — How many days old are you
#  /bmi <weight> <height>— BMI calculator
#  /emi <loan> <rate> <years> — EMI calculator
#  /gpa                  — GPA / percentage converter
#  /timezone <city>      — Current time in any city
# ============================================================

import random
import requests
import os
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# Active typing tests & math quizzes
typing_tests: dict[str, dict] = {}
math_quizzes: dict[str, dict] = {}


def _groq(system: str, user: str, max_tokens: int = 300, temp: float = 0.7) -> str:
    resp = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens, "temperature": temp,
        },
        timeout=20,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── /forecast ─────────────────────────────────────────────

WEATHER_ICONS = {
    "Sunny": "☀️", "Clear": "🌙", "Partly cloudy": "⛅",
    "Cloudy": "☁️", "Overcast": "🌫️", "Mist": "🌫️",
    "Rain": "🌧️", "Drizzle": "🌦️", "Thunder": "⛈️",
    "Snow": "❄️", "Fog": "🌁", "Blizzard": "🌨️",
}

def _weather_icon(desc: str) -> str:
    for key, icon in WEATHER_ICONS.items():
        if key.lower() in desc.lower():
            return icon
    return "🌡️"


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/forecast [city] — 3-day weather forecast."""
    import json as _json
    import os as _os

    user_id = str(update.effective_user.id)

    if not context.args:
        # Try saved city
        city = None
        if _os.path.exists("user_prefs.json"):
            with open("user_prefs.json") as f:
                prefs = _json.load(f)
            city = prefs.get(user_id, {}).get("city")
        if not city:
            await update.message.reply_text(
                "⛅ *3-Day Forecast*\n\n"
                "`/forecast Mumbai`\n"
                "`/forecast Delhi`\n"
                "Or set your city: `/setcity Kanpur`",
                parse_mode="Markdown"
            )
            return
    else:
        city = " ".join(context.args)

    await update.message.chat.send_action("typing")

    try:
        url  = f"https://wttr.in/{city}?format=j1"
        data = requests.get(url, timeout=8).json()

        weather = data.get("weather", [])
        if not weather:
            await update.message.reply_text(f"❌ No forecast data for *{city}*.", parse_mode="Markdown")
            return

        lines = [f"⛅ *3-Day Forecast — {city.title()}*\n"]

        for i, day in enumerate(weather[:3]):
            date_str  = day.get("date", "")
            max_c     = day.get("maxtempC", "?")
            min_c     = day.get("mintempC", "?")
            desc      = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "N/A")
            rain_mm   = day.get("hourly", [{}])[4].get("precipMM", "0")
            uv        = day.get("uvIndex", "?")
            icon      = _weather_icon(desc)

            try:
                d = datetime.strptime(date_str, "%Y-%m-%d")
                day_name = "Today" if i == 0 else ("Tomorrow" if i == 1 else d.strftime("%A"))
            except Exception:
                day_name = f"Day {i+1}"

            lines.append(
                f"📅 *{day_name}* ({date_str})\n"
                f"{icon} {desc}\n"
                f"🌡 {min_c}°C — {max_c}°C\n"
                f"🌧 Rain: {rain_mm}mm  ☀️ UV: {uv}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Forecast unavailable for *{city}*. Try again!", parse_mode="Markdown")


# ── /news <topic> ─────────────────────────────────────────

async def topicnews_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/topicnews <keyword> — Search news by topic using RSS."""
    if not context.args:
        await update.message.reply_text(
            "📰 *Topic News Search*\n\n"
            "`/topicnews India`\n"
            "`/topicnews AI technology`\n"
            "`/topicnews cricket`\n"
            "`/topicnews bitcoin`\n"
            "`/topicnews Bollywood`",
            parse_mode="Markdown"
        )
        return

    topic = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        encoded = requests.utils.quote(topic)
        # Google News RSS (no API key needed)
        url  = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})

        import xml.etree.ElementTree as ET
        root  = ET.fromstring(resp.content)
        items = root.findall(".//item")[:5]

        if not items:
            await update.message.reply_text(f"❌ No news found for *{topic}*.", parse_mode="Markdown")
            return

        lines = [f"📰 *News: {topic.title()}*\n"]
        for i, item in enumerate(items, 1):
            title  = item.findtext("title", "").split(" - ")[0]  # Remove source suffix
            source = item.findtext("source", "")
            link   = item.findtext("link", "")
            pub    = item.findtext("pubDate", "")[:16]
            lines.append(f"*{i}.* {title}\n   _{source}_ · {pub}\n   🔗 {link}\n")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        await update.message.reply_text(f"❌ News search failed. Try again!\n`{str(e)[:80]}`", parse_mode="Markdown")


# ── /dictionary ───────────────────────────────────────────

async def dictionary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dictionary <word> — Full: meaning + synonyms + example + Hindi."""
    if not context.args:
        await update.message.reply_text(
            "📚 *Enhanced Dictionary*\n\n"
            "`/dictionary ephemeral`\n"
            "`/dictionary serendipity`\n"
            "`/dictionary algorithm`\n\n"
            "Gets: meaning + synonyms + example + Hindi translation!",
            parse_mode="Markdown"
        )
        return

    word = context.args[0].lower().strip()
    await update.message.chat.send_action("typing")

    try:
        # 1. Dictionary API for definition + synonyms
        dict_resp = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
            timeout=6
        )
        dict_data  = dict_resp.json()
        entry      = dict_data[0] if isinstance(dict_data, list) else {}
        phonetic   = entry.get("phonetic", "")
        meanings   = entry.get("meanings", [])

        lines = [f"📚 *{word.capitalize()}*  _{phonetic}_\n"]

        for meaning in meanings[:2]:
            pos  = meaning.get("partOfSpeech", "")
            defs = meaning.get("definitions", [])[:2]
            syns = meaning.get("synonyms", [])[:5]

            lines.append(f"_{pos}_")
            for i, d in enumerate(defs, 1):
                defn = d.get("definition", "")
                ex   = d.get("example", "")
                lines.append(f"  {i}. {defn}")
                if ex:
                    lines.append(f'     _e.g. "{ex}"_')
            if syns:
                lines.append(f"  📌 Synonyms: {', '.join(syns)}\n")
            else:
                lines.append("")

        # 2. Hindi translation via MyMemory
        try:
            trans_resp = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": word, "langpair": "en|hi"},
                timeout=6
            )
            hindi = trans_resp.json()["responseData"]["translatedText"]
            if hindi and hindi.lower() != word.lower():
                lines.append(f"🇮🇳 *Hindi:* {hindi}")
        except Exception:
            pass

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception:
        # Fallback to AI
        try:
            result = _groq(
                system="You are a dictionary. For the given word provide: 1) Part of speech, 2) Clear definition, 3) Example sentence, 4) 3 synonyms, 5) Hindi meaning. Be concise.",
                user=f"Word: {word}",
                max_tokens=250
            )
            await update.message.reply_text(f"📚 *{word.capitalize()}*\n\n{result}", parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("❌ Dictionary unavailable. Try again!")


# ── /tip ──────────────────────────────────────────────────

async def tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tip <topic> — Get a quick actionable pro tip."""
    if not context.args:
        await update.message.reply_text(
            "💡 *Pro Tip Generator*\n\n"
            "`/tip Python`\n"
            "`/tip studying`\n"
            "`/tip time management`\n"
            "`/tip fitness`\n"
            "`/tip public speaking`\n"
            "`/tip saving money`",
            parse_mode="Markdown"
        )
        return

    topic = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        tip = _groq(
            system=(
                "You are a life coach and expert advisor. Give ONE specific, actionable, "
                "immediately-useful pro tip on the given topic. "
                "Format: Start with a relevant emoji, then the tip in 2-3 sentences. "
                "End with one quick action the person can take RIGHT NOW."
            ),
            user=f"Give a pro tip about: {topic}",
            max_tokens=180,
            temp=0.8,
        )
        await update.message.reply_text(
            f"💡 *Pro Tip: {topic.title()}*\n\n{tip}\n\n_Want another? /tip {topic}_",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Tip generator unavailable. Try again!")


# ── /random ───────────────────────────────────────────────

RANDOM_CATEGORIES = ["fact", "quote", "joke", "tip", "word", "riddle"]


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/random — Get a random useful thing."""
    category = random.choice(RANDOM_CATEGORIES)
    await update.message.chat.send_action("typing")

    try:
        if category == "fact":
            result = _groq("Give one amazing, mind-blowing fact. Start with 🤯 emoji. 2 sentences max.", "Surprise me with a fact!", 100, 0.9)
            await update.message.reply_text(f"🎲 Random Fact!\n\n{result}\n\n_More: /fact_")
        elif category == "quote":
            result = _groq("Give one powerful motivational quote with the author's name. Format: 'Quote' — Author", "Inspire me!", 80, 0.8)
            await update.message.reply_text(f"🎲 Random Quote!\n\n💬 {result}\n\n_More: /quote_")
        elif category == "joke":
            result = _groq("Tell one short, clever programming or student joke. Setup + punchline format.", "Make me laugh!", 100, 0.9)
            await update.message.reply_text(f"🎲 Random Joke!\n\n{result}\n\n_More: /joke_")
        elif category == "tip":
            topic = random.choice(["productivity", "coding", "health", "studying", "money", "communication"])
            result = _groq("Give ONE quick actionable pro tip. 2 sentences. Start with relevant emoji.", f"Topic: {topic}", 100, 0.8)
            await update.message.reply_text(f"🎲 Random Tip: {topic.title()}!\n\n{result}\n\n_More: /tip {topic}_")
        elif category == "riddle":
            result = _groq("Give a clever riddle. Format: 'Riddle: <riddle>\n\nAnswer: ||<answer>||' Use spoiler tags for answer.", "Give me a riddle!", 120, 0.8)
            await update.message.reply_text(f"🎲 Random Riddle!\n\n{result}")
        else:
            result = _groq("Give me one interesting English word with its meaning. Format: Word: <word>\nMeaning: <meaning>\nFun fact: <something interesting about it>", "Word of the moment!", 100, 0.7)
            await update.message.reply_text(f"🎲 Random Word!\n\n📚 {result}\n\n_More: /word_")
    except Exception:
        await update.message.reply_text("🎲 Try: /fact · /quote · /joke · /tip Python")


# ── /word ─────────────────────────────────────────────────

async def word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/word — Word of the day with meaning, usage, and Hindi."""
    await update.message.chat.send_action("typing")
    try:
        result = _groq(
            system=(
                "You are a vocabulary teacher. Give the Word of the Day.\n"
                "Format EXACTLY:\n"
                "📖 Word: <word>\n"
                "🗣 Pronunciation: <phonetic>\n"
                "📝 Meaning: <clear definition>\n"
                "💬 Example: <natural example sentence>\n"
                "🇮🇳 Hindi: <Hindi meaning>\n"
                "🌟 Why learn it: <one interesting reason>\n"
            ),
            user="Give me today's interesting English word to learn.",
            max_tokens=200,
            temp=0.85,
        )
        await update.message.reply_text(f"🌟 Word of the Day!\n\n{result}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Word service unavailable. Try /dictionary <any word>!")


# ── /mathquiz ─────────────────────────────────────────────

def _make_math_question() -> tuple[str, int]:
    level = random.choice(["easy", "medium", "hard"])
    if level == "easy":
        a, b = random.randint(2, 20), random.randint(2, 20)
        op   = random.choice(["+", "-", "×"])
    elif level == "medium":
        a, b = random.randint(10, 50), random.randint(2, 12)
        op   = random.choice(["+", "-", "×", "÷"])
    else:
        a, b = random.randint(10, 99), random.randint(2, 9)
        op   = random.choice(["×", "÷", "²"])

    if op == "+":
        ans = a + b
    elif op == "-":
        ans = a - b
    elif op == "×":
        ans = a * b
    elif op == "÷":
        b   = random.choice([2, 3, 4, 5, 6, 10])
        a   = b * random.randint(2, 12)
        ans = a // b
    else:  # ²
        ans = a * a
        return f"{a}²", ans

    return f"{a} {op} {b}", ans


async def mathquiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mathquiz — Quick mental math quiz with tap answers."""
    question, correct = _make_math_question()
    user_id = str(update.effective_user.id)

    # Generate 3 wrong answers close to correct
    wrongs = set()
    while len(wrongs) < 3:
        offset = random.choice([-3, -2, -1, 1, 2, 3, 5, -5])
        w = correct + offset
        if w != correct and w > 0:
            wrongs.add(w)

    options = list(wrongs) + [correct]
    random.shuffle(options)

    math_quizzes[user_id] = {"answer": correct, "question": question}

    keyboard = [
        [InlineKeyboardButton(str(opt), callback_data=f"mq|{user_id}|{opt}") for opt in options[:2]],
        [InlineKeyboardButton(str(opt), callback_data=f"mq|{user_id}|{opt}") for opt in options[2:]],
    ]

    await update.message.reply_text(
        f"🧮 *Mental Math!*\n\n"
        f"What is *{question}* = ?\n\n"
        f"_Tap the correct answer:_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def mathquiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    if not query.data.startswith("mq|"):
        return

    parts   = query.data.split("|")
    user_id = parts[1]
    chosen  = int(parts[2])

    quiz = math_quizzes.pop(user_id, None)
    if not quiz:
        await query.edit_message_text("⏰ Quiz expired. Get a new one: /mathquiz")
        return

    correct  = quiz["answer"]
    question = quiz["question"]

    if chosen == correct:
        await query.edit_message_text(
            f"✅ *Correct!* {question} = *{correct}*\n\n🧠 Try another: /mathquiz",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"❌ *Wrong!* You chose {chosen}\n"
            f"✅ Correct answer: *{question} = {correct}*\n\nTry again: /mathquiz",
            parse_mode="Markdown"
        )


# ── /typetest ─────────────────────────────────────────────

TYPETEST_SENTENCES = [
    "The quick brown fox jumps over the lazy dog",
    "Python is a powerful and beginner-friendly programming language",
    "Practice makes perfect when it comes to typing speed",
    "Technology is best when it brings people together",
    "Never stop learning because life never stops teaching",
    "The best time to plant a tree was twenty years ago",
    "Code is like humor when you have to explain it it is bad",
    "First solve the problem then write the code",
    "A computer once beat me at chess but it was no match at kickboxing",
    "India is a land of diversity culture and incredible talent",
]


async def typetest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/typetest — Test your typing speed."""
    sentence = random.choice(TYPETEST_SENTENCES)
    user_id  = str(update.effective_user.id)

    typing_tests[user_id] = {
        "sentence": sentence,
        "start":    datetime.now().timestamp(),
        "words":    len(sentence.split()),
    }

    await update.message.reply_text(
        f"⌨️ *Typing Speed Test!*\n\n"
        f"Type this sentence exactly:\n\n"
        f"```\n{sentence}\n```\n\n"
        f"_Start typing NOW! ⏱_",
        parse_mode="Markdown"
    )


async def typetest_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Called from smart_message_handler — checks if user is in a typing test."""
    user_id = str(update.effective_user.id)
    if user_id not in typing_tests:
        return False

    test     = typing_tests.pop(user_id)
    elapsed  = datetime.now().timestamp() - test["start"]
    typed    = update.message.text.strip()
    expected = test["sentence"]
    words    = test["words"]

    # Calculate WPM
    wpm      = int((words / elapsed) * 60) if elapsed > 0 else 0

    # Calculate accuracy
    typed_words    = typed.split()
    expected_words = expected.split()
    correct_words  = sum(1 for a, b in zip(typed_words, expected_words) if a.lower() == b.lower())
    accuracy       = int(correct_words / len(expected_words) * 100) if expected_words else 0

    if accuracy >= 90:
        grade = "🏆 Excellent!"
    elif accuracy >= 70:
        grade = "✅ Good job!"
    elif accuracy >= 50:
        grade = "📚 Keep practicing!"
    else:
        grade = "🔄 Try again!"

    await update.message.reply_text(
        f"⌨️ *Typing Test Results*\n\n"
        f"⏱ Time: *{elapsed:.1f}s*\n"
        f"🚀 Speed: *{wpm} WPM*\n"
        f"🎯 Accuracy: *{accuracy}%*\n"
        f"✅ Correct words: {correct_words}/{len(expected_words)}\n\n"
        f"{grade}\n\n"
        f"_Try again: /typetest_",
        parse_mode="Markdown"
    )
    return True


# ── /agedays ─────────────────────────────────────────────

async def agedays_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/agedays <DD-MM-YYYY> — How many days old are you?"""
    if not context.args:
        await update.message.reply_text(
            "🎂 *Age in Days*\n\n"
            "`/agedays 15-08-2004`\n"
            "`/agedays 01-01-2000`\n\n"
            "Find out exactly how many days you've been alive!",
            parse_mode="Markdown"
        )
        return

    try:
        birth   = datetime.strptime(context.args[0], "%d-%m-%Y").date()
        today   = date.today()
        delta   = today - birth
        days    = delta.days
        years   = days // 365
        months  = (days % 365) // 30
        weeks   = days // 7
        hours   = days * 24
        minutes = hours * 60

        next_bday = birth.replace(year=today.year)
        if next_bday < today:
            next_bday = next_bday.replace(year=today.year + 1)
        days_to_bday = (next_bday - today).days

        await update.message.reply_text(
            f"🎂 *Age Calculator*\n\n"
            f"📅 Born: {birth.strftime('%d %B %Y')}\n\n"
            f"🗓 Age: *{years} years, {months} months*\n"
            f"📆 Days alive: *{days:,} days*\n"
            f"📅 Weeks: *{weeks:,} weeks*\n"
            f"⏰ Hours: *{hours:,} hours*\n"
            f"⏱ Minutes: *{minutes:,} minutes*\n\n"
            f"🎉 Next birthday in: *{days_to_bday} days!*",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid date! Use DD-MM-YYYY\nExample: `/agedays 15-08-2004`", parse_mode="Markdown")


# ── /bmi ─────────────────────────────────────────────────

async def bmi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bmi <weight_kg> <height_cm> — Calculate BMI."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚖️ *BMI Calculator*\n\n"
            "`/bmi 65 170` — 65 kg, 170 cm\n"
            "`/bmi 75 175`\n\n"
            "Format: `/bmi <weight in kg> <height in cm>`",
            parse_mode="Markdown"
        )
        return

    try:
        weight = float(context.args[0])
        height = float(context.args[1]) / 100  # cm to m
        bmi    = weight / (height ** 2)

        if bmi < 18.5:
            cat, emoji, advice = "Underweight", "⚠️", "Consider eating more nutritious food and consult a doctor."
        elif bmi < 25:
            cat, emoji, advice = "Normal weight", "✅", "Great! Maintain your healthy lifestyle."
        elif bmi < 30:
            cat, emoji, advice = "Overweight", "⚠️", "Consider more exercise and a balanced diet."
        else:
            cat, emoji, advice = "Obese", "🔴", "Consult a doctor for a personalized health plan."

        bar_filled = min(int(bmi / 4), 10)
        bar = "🟩" * min(bar_filled, 6) + "🟨" * max(0, min(bar_filled - 6, 2)) + "🟥" * max(0, bar_filled - 8)

        await update.message.reply_text(
            f"⚖️ *BMI Calculator*\n\n"
            f"⚖️ Weight: {weight} kg\n"
            f"📏 Height: {context.args[1]} cm\n\n"
            f"📊 BMI: *{bmi:.1f}*\n"
            f"{bar}\n"
            f"{emoji} Category: *{cat}*\n\n"
            f"💡 {advice}\n\n"
            f"_Note: BMI is a general indicator. Consult a doctor for health advice._",
            parse_mode="Markdown"
        )
    except (ValueError, ZeroDivisionError):
        await update.message.reply_text("❌ Invalid input. Usage: `/bmi 65 170`", parse_mode="Markdown")


# ── /emi ──────────────────────────────────────────────────

async def emi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/emi <loan_amount> <annual_rate_%> <years> — Calculate EMI."""
    if len(context.args) < 3:
        await update.message.reply_text(
            "🏦 *EMI Calculator*\n\n"
            "`/emi 500000 8.5 5` — ₹5 lakh loan, 8.5%, 5 years\n"
            "`/emi 1000000 9 20` — ₹10 lakh home loan, 9%, 20 years\n\n"
            "Format: `/emi <amount> <annual_rate_%> <years>`",
            parse_mode="Markdown"
        )
        return

    try:
        principal = float(context.args[0])
        rate      = float(context.args[1]) / 100 / 12  # monthly rate
        months    = int(context.args[2]) * 12

        if rate == 0:
            emi = principal / months
        else:
            emi = principal * rate * (1 + rate) ** months / ((1 + rate) ** months - 1)

        total_paid     = emi * months
        total_interest = total_paid - principal

        def fmt(n):
            if n >= 1e7:
                return f"₹{n/1e7:.2f} Cr"
            elif n >= 1e5:
                return f"₹{n/1e5:.2f} L"
            else:
                return f"₹{n:,.0f}"

        await update.message.reply_text(
            f"🏦 *EMI Calculator*\n\n"
            f"💰 Loan Amount: {fmt(principal)}\n"
            f"📈 Interest Rate: {context.args[1]}% per year\n"
            f"📅 Tenure: {context.args[2]} years ({months} months)\n\n"
            f"━━━━━━━━━━━━━━\n"
            f"💳 Monthly EMI: *{fmt(emi)}*\n"
            f"💸 Total Payment: {fmt(total_paid)}\n"
            f"🏦 Total Interest: {fmt(total_interest)}\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"_Tip: Higher down payment = lower EMI!_",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Invalid input. Usage: `/emi 500000 8.5 5`", parse_mode="Markdown")


# ── /gpa ─────────────────────────────────────────────────

async def gpa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gpa <percentage> — Convert percentage to GPA and grade."""
    if not context.args:
        await update.message.reply_text(
            "🎓 *GPA / Grade Converter*\n\n"
            "`/gpa 85` — 85% to GPA\n"
            "`/gpa 72`\n"
            "`/gpa 95`",
            parse_mode="Markdown"
        )
        return

    try:
        pct = float(context.args[0])
        if not (0 <= pct <= 100):
            raise ValueError

        # 10-point GPA scale (common in Indian universities)
        gpa_10 = round(pct / 9.5, 2)
        gpa_10 = min(gpa_10, 10.0)

        # 4-point GPA scale (US style)
        if pct >= 90:
            gpa_4, grade, remark = 4.0, "O (Outstanding)", "🏆 Exceptional!"
        elif pct >= 80:
            gpa_4, grade, remark = 3.7, "A+ (Excellent)", "⭐ Excellent!"
        elif pct >= 70:
            gpa_4, grade, remark = 3.3, "A (Very Good)", "✅ Very Good!"
        elif pct >= 60:
            gpa_4, grade, remark = 3.0, "B+ (Good)", "👍 Good!"
        elif pct >= 50:
            gpa_4, grade, remark = 2.0, "B (Average)", "📚 Keep going!"
        elif pct >= 40:
            gpa_4, grade, remark = 1.0, "C (Pass)", "⚠️ Need to improve!"
        else:
            gpa_4, grade, remark = 0.0, "F (Fail)", "❌ Study harder!"

        await update.message.reply_text(
            f"🎓 *Grade Conversion*\n\n"
            f"📊 Percentage: *{pct}%*\n\n"
            f"🇮🇳 Indian GPA (10-pt): *{gpa_10}*\n"
            f"🇺🇸 US GPA (4-pt): *{gpa_4}*\n"
            f"📝 Grade: *{grade}*\n\n"
            f"{remark}",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ Enter a percentage between 0-100.\nExample: `/gpa 85`", parse_mode="Markdown")


# ── /timezone ─────────────────────────────────────────────

TIMEZONES = {
    "india": ("Asia/Kolkata", "🇮🇳"),
    "ist": ("Asia/Kolkata", "🇮🇳"),
    "new york": ("America/New_York", "🇺🇸"),
    "usa": ("America/New_York", "🇺🇸"),
    "london": ("Europe/London", "🇬🇧"),
    "uk": ("Europe/London", "🇬🇧"),
    "dubai": ("Asia/Dubai", "🇦🇪"),
    "uae": ("Asia/Dubai", "🇦🇪"),
    "tokyo": ("Asia/Tokyo", "🇯🇵"),
    "japan": ("Asia/Tokyo", "🇯🇵"),
    "sydney": ("Australia/Sydney", "🇦🇺"),
    "australia": ("Australia/Sydney", "🇦🇺"),
    "paris": ("Europe/Paris", "🇫🇷"),
    "berlin": ("Europe/Berlin", "🇩🇪"),
    "moscow": ("Europe/Moscow", "🇷🇺"),
    "beijing": ("Asia/Shanghai", "🇨🇳"),
    "china": ("Asia/Shanghai", "🇨🇳"),
    "singapore": ("Asia/Singapore", "🇸🇬"),
    "toronto": ("America/Toronto", "🇨🇦"),
    "canada": ("America/Toronto", "🇨🇦"),
}


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/timezone <city/country> — Current time in any city."""
    if not context.args:
        cities = " · ".join(f"`{k}`" for k in list(TIMEZONES.keys())[:8])
        await update.message.reply_text(
            f"🌐 *World Clock*\n\n"
            f"Available: {cities} and more\n\n"
            f"Example: `/timezone Dubai`\n"
            f"`/timezone Tokyo`",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args).lower()

    if query not in TIMEZONES:
        # Try partial match
        match = next((k for k in TIMEZONES if query in k or k in query), None)
        if not match:
            await update.message.reply_text(
                f"❌ City/country *{query}* not found.\n\n"
                f"Try: india, london, dubai, tokyo, usa, australia",
                parse_mode="Markdown"
            )
            return
        query = match

    tz_name, flag = TIMEZONES[query]

    try:
        from datetime import timezone as tz
        import zoneinfo
        zone     = zoneinfo.ZoneInfo(tz_name)
        now      = datetime.now(zone)
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %d %B %Y")
        offset   = now.strftime("%z")
        offset_h = f"UTC{offset[:3]}:{offset[3:]}"

        # Compare with IST
        ist_zone = zoneinfo.ZoneInfo("Asia/Kolkata")
        ist_now  = datetime.now(ist_zone)
        diff_sec = (now.utcoffset() - ist_now.utcoffset()).total_seconds()
        diff_h   = diff_sec / 3600
        diff_str = f"+{diff_h:.0f}h" if diff_h >= 0 else f"{diff_h:.0f}h"

        await update.message.reply_text(
            f"🌐 *World Clock — {query.title()}* {flag}\n\n"
            f"🕐 Time: *{time_str}*\n"
            f"📅 Date: {date_str}\n"
            f"⏰ Timezone: {tz_name}\n"
            f"🌍 Offset: {offset_h}\n"
            f"🇮🇳 vs IST: {diff_str} from India",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Could not get time for *{query}*.\nError: {str(e)[:60]}", parse_mode="Markdown")
