# ============================================================
#  handlers/ai_extras.py
#  /imagine <prompt>   — AI image description + ASCII art
#  /explain <topic>    — Explain at 5/teen/expert level
#  /code <task>        — Generate code in any language
#  /quiz <topic>       — AI-generated custom quiz
# ============================================================

import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# Active quizzes: { user_id: { question, answer, options } }
active_quizzes: dict[str, dict] = {}


def _groq(system: str, user: str, max_tokens: int = 500, temp: float = 0.7) -> str:
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
            "temperature": temp,
        },
        timeout=25,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── /imagine ──────────────────────────────────────────────

ASCII_FRAMES = {
    "landscape": """
🖼 *AI Image Vision*

```
 ☀️  ~~~  🌤  ~~~
🏔️🏔️🌲🌲🌲🏡🌲🌲
🌊〰〰〰〰〰〰〰〰
```""",
    "space": """
🖼 *AI Image Vision*

```
✨  .  ·  ★  .  ✨
  🌍    ·  ★   🌙
·  ·  🚀  ·  ·  ·
★    ·    ·  ★  ·
```""",
    "city": """
🖼 *AI Image Vision*

```
🌃🌃🌃🌃🌃🌃🌃
🏢🏬🏦🏢🏣🏢🏬
🚗🚕🚙🛻🚌🏍🚗
```""",
    "default": """
🖼 *AI Image Vision*

```
✨ · · · · · · ✨
·  🎨  ·  🖌️  · ·
· · ·  🖼️  · · · ·
✨ · · · · · · ✨
```""",
}


async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/imagine <prompt> — AI describes an image in vivid detail."""
    if not context.args:
        await update.message.reply_text(
            "🎨 *AI Image Imagination*\n\n"
            "I can't generate real images, but I'll paint one with words!\n\n"
            "`/imagine a sunset over the Himalayas`\n"
            "`/imagine a futuristic city in 2150`\n"
            "`/imagine a dragon sleeping on gold coins`\n"
            "`/imagine a cozy Indian chai shop in rain`",
            parse_mode="Markdown"
        )
        return

    prompt = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        description = _groq(
            system=(
                "You are a vivid, poetic AI artist. When given a scene prompt, "
                "describe it in stunning visual detail as if painting it with words. "
                "Use 4-6 sentences covering: lighting, colors, mood, textures, atmosphere. "
                "Make it cinematic and beautiful. End with one creative observation."
            ),
            user=f"Paint this scene with words: {prompt}",
            max_tokens=300,
            temp=0.9,
        )

        # Pick ASCII frame based on keywords
        frame_key = "default"
        p_lower = prompt.lower()
        if any(w in p_lower for w in ["mountain", "forest", "river", "sky", "sunset", "nature"]):
            frame_key = "landscape"
        elif any(w in p_lower for w in ["space", "galaxy", "star", "planet", "cosmos", "moon"]):
            frame_key = "space"
        elif any(w in p_lower for w in ["city", "street", "urban", "building", "night"]):
            frame_key = "city"

        ascii_art = ASCII_FRAMES[frame_key]

        await update.message.reply_text(
            f"{ascii_art}\n\n"
            f"🎨 *Prompt:* _{prompt}_\n\n"
            f"🖌 {description}",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text("❌ Imagination engine unavailable. Try again!")


# ── /explain ─────────────────────────────────────────────

EXPLAIN_LEVELS = {
    "5":      ("a 5-year-old child", "Use toys, candy, and simple stories as analogies. Very short, super simple."),
    "kid":    ("a 5-year-old child", "Use toys, candy, and simple stories as analogies. Very short, super simple."),
    "teen":   ("a curious 15-year-old student", "Use relatable examples from school, games, and daily life. Clear and engaging."),
    "simple": ("a curious 15-year-old student", "Use relatable examples from school, games, and daily life. Clear and engaging."),
    "expert": ("a domain expert or graduate student", "Use technical terms, precise language, and depth. Assume strong background knowledge."),
    "bca":    ("a BCA (Bachelor of Computer Applications) student", "Use CS fundamentals, simple code examples, and Indian academic context."),
}


async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/explain <topic> [for 5/teen/expert/bca] — Multi-level explanations."""
    if not context.args:
        await update.message.reply_text(
            "🧠 *Explain Anything!*\n\n"
            "`/explain recursion` — default (BCA student level)\n"
            "`/explain DNA for 5` — explain like I'm 5\n"
            "`/explain blockchain for teen` — simple explanation\n"
            "`/explain quantum computing for expert` — deep dive\n"
            "`/explain inheritance for bca` — CS student level\n\n"
            "Levels: `5` · `teen` · `expert` · `bca`",
            parse_mode="Markdown"
        )
        return

    args    = context.args
    level   = "bca"  # default
    topic   = " ".join(args)

    # Check for "for <level>" at end
    if len(args) >= 2 and args[-1].lower() in EXPLAIN_LEVELS:
        level = args[-1].lower()
        topic = " ".join(args[:-1])
    elif len(args) >= 3 and args[-2].lower() == "for" and args[-1].lower() in EXPLAIN_LEVELS:
        level = args[-1].lower()
        topic = " ".join(args[:-2])

    audience, style = EXPLAIN_LEVELS[level]
    await update.message.chat.send_action("typing")

    try:
        explanation = _groq(
            system=(
                f"You are a brilliant teacher explaining to {audience}. "
                f"{style} "
                "Keep it concise (5-8 sentences). Use bullet points if helpful. "
                "End with one interesting real-world example."
            ),
            user=f"Explain: {topic}",
            max_tokens=450,
            temp=0.6,
        )

        level_labels = {
            "5": "👶 Like You're 5", "kid": "👶 Like You're 5",
            "teen": "🧒 Teen Level", "simple": "🧒 Simple",
            "expert": "🎓 Expert Level", "bca": "💻 BCA Student Level"
        }
        label       = level_labels.get(level, "💡 Explained")
        safe_topic  = topic.replace("*", "").replace("_", "").replace("`", "")

        # Send plain text to avoid Markdown parse errors from AI response
        await update.message.reply_text(
            f"🧠 {label}: {safe_topic.title()}\n\n{explanation}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Explanation engine error: {str(e)[:100]}\nTry again!")


# ── /code ────────────────────────────────────────────────

LANG_ALIASES = {
    "py": "python", "js": "javascript", "ts": "typescript",
    "cpp": "c++", "cs": "c#", "rb": "ruby", "rs": "rust",
    "go": "golang", "kt": "kotlin", "sh": "bash",
}


async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/code <task> [in <language>] — Generate code snippet."""
    if not context.args:
        await update.message.reply_text(
            "💻 *Code Generator*\n\n"
            "`/code fibonacci sequence in python`\n"
            "`/code REST API with express in javascript`\n"
            "`/code bubble sort in java`\n"
            "`/code login form in HTML CSS`\n"
            "`/code binary search in c++`\n\n"
            "Just describe what you need!",
            parse_mode="Markdown"
        )
        return

    task    = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        code_response = _groq(
            system=(
                "You are an expert programmer and coding tutor. "
                "When given a coding task, provide:\n"
                "1. Clean, working code with comments\n"
                "2. A 2-3 sentence explanation of how it works\n"
                "3. One tip for improvement or common pitfall\n"
                "Keep code concise but complete. "
                "If no language specified, use Python."
            ),
            user=f"Write code for: {task}",
            max_tokens=600,
            temp=0.3,
        )

        await update.message.reply_text(
            f"💻 *Code: {task.title()}*\n\n{code_response}",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Code generator unavailable. Try again!")


# ── /quiz ────────────────────────────────────────────────

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/quiz <topic> — AI generates a custom MCQ quiz."""
    if not context.args:
        await update.message.reply_text(
            "📝 *AI Custom Quiz*\n\n"
            "I'll generate an MCQ on any topic!\n\n"
            "`/quiz Python basics`\n"
            "`/quiz World War 2`\n"
            "`/quiz Human anatomy`\n"
            "`/quiz Data structures`\n"
            "`/quiz Indian history`",
            parse_mode="Markdown"
        )
        return

    topic   = " ".join(context.args)
    user_id = str(update.effective_user.id)
    await update.message.chat.send_action("typing")

    try:
        raw = _groq(
            system=(
                "You are a quiz master. Generate ONE multiple choice question on the given topic.\n"
                "Respond in EXACTLY this format (no extra text):\n"
                "QUESTION: <question text>\n"
                "A: <option A>\n"
                "B: <option B>\n"
                "C: <option C>\n"
                "D: <option D>\n"
                "ANSWER: <A or B or C or D>\n"
                "EXPLANATION: <one sentence why>"
            ),
            user=f"Topic: {topic}",
            max_tokens=300,
            temp=0.7,
        )

        # Parse the response
        lines = {l.split(":")[0].strip(): ":".join(l.split(":")[1:]).strip()
                 for l in raw.strip().split("\n") if ":" in l}

        question    = lines.get("QUESTION", "")
        opt_a       = lines.get("A", "")
        opt_b       = lines.get("B", "")
        opt_c       = lines.get("C", "")
        opt_d       = lines.get("D", "")
        answer      = lines.get("ANSWER", "").strip().upper()
        explanation = lines.get("EXPLANATION", "")

        if not question or answer not in ("A", "B", "C", "D"):
            raise ValueError("Bad parse")

        # Store active quiz
        active_quizzes[user_id] = {
            "answer": answer,
            "explanation": explanation,
            "topic": topic,
        }

        keyboard = [
            [InlineKeyboardButton(f"🅐 {opt_a}", callback_data=f"quiz|{user_id}|A")],
            [InlineKeyboardButton(f"🅑 {opt_b}", callback_data=f"quiz|{user_id}|B")],
            [InlineKeyboardButton(f"🅒 {opt_c}", callback_data=f"quiz|{user_id}|C")],
            [InlineKeyboardButton(f"🅓 {opt_d}", callback_data=f"quiz|{user_id}|D")],
        ]

        await update.message.reply_text(
            f"📝 *Quiz: {topic.title()}*\n\n"
            f"❓ {question}\n\n"
            f"_Tap your answer:_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text(
            "❌ Quiz generation failed. Try again!\n"
            "Tip: be specific — `/quiz Python lists` not just `/quiz Python`"
        )


async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz answer button taps."""
    query   = update.callback_query
    await query.answer()
    if not query.data.startswith("quiz|"):
        return

    parts    = query.data.split("|")
    owner_id = parts[1]
    chosen   = parts[2]

    quiz = active_quizzes.get(owner_id)
    if not quiz:
        await query.edit_message_text("⏰ This quiz has expired! Get a new one: /quiz")
        return

    correct_letter = quiz["answer"]
    explanation    = quiz["explanation"]
    topic          = quiz["topic"]
    del active_quizzes[owner_id]

    if chosen == correct_letter:
        result = f"✅ *Correct! Well done!*\n\n"
    else:
        result = f"❌ *Wrong!* Correct answer was: *{correct_letter}*\n\n"

    await query.edit_message_text(
        f"{result}"
        f"💡 {explanation}\n\n"
        f"_Another question? /quiz {topic}_",
        parse_mode="Markdown"
    )
