# ============================================================
#  handlers/student_tools.py
#  /flashcard add/quiz/list/clear — Flashcard study system
#  /mcq <topic>                   — AI MCQ practice
#  /essay <topic>                 — AI essay outline
#  /formula <subject>             — Quick formula reference
# ============================================================

import json
import os
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

FLASHCARD_FILE = "flashcards.json"

# Active flashcard quiz sessions: { user_id: { cards: [...], idx: 0, score: 0 } }
active_flashcard_sessions: dict[str, dict] = {}


def _groq(system: str, user: str, max_tokens: int = 500, temp: float = 0.6) -> str:
    resp = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temp,
        },
        timeout=25,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── Flashcard helpers ─────────────────────────────────────

def load_flashcards() -> dict:
    if os.path.exists(FLASHCARD_FILE):
        with open(FLASHCARD_FILE) as f:
            return json.load(f)
    return {}


def save_flashcards(data: dict):
    with open(FLASHCARD_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── /flashcard ────────────────────────────────────────────

async def flashcard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /flashcard add <front> | <back>   — Add a card
    /flashcard list                   — List all cards
    /flashcard quiz                   — Start quiz session
    /flashcard clear                  — Delete all cards
    """
    user_id = str(update.effective_user.id)

    if not context.args:
        cards = load_flashcards().get(user_id, [])
        await update.message.reply_text(
            f"🗂 *Flashcard System*\n\n"
            f"You have *{len(cards)}* card(s).\n\n"
            f"`/flashcard add Python | A programming language`\n"
            f"`/flashcard add RAM | Random Access Memory`\n"
            f"`/flashcard list` — View all your cards\n"
            f"`/flashcard quiz` — Start a quiz session\n"
            f"`/flashcard clear` — Delete all cards\n\n"
            f"_Separate front and back with a pipe `|`_",
            parse_mode="Markdown"
        )
        return

    sub = context.args[0].lower()
    all_cards = load_flashcards()

    if sub == "add":
        full = " ".join(context.args[1:])
        if "|" not in full:
            await update.message.reply_text(
                "❌ Use a pipe `|` to separate front and back.\n"
                "Example: `/flashcard add OSI Model | 7-layer networking model`",
                parse_mode="Markdown"
            )
            return
        parts = full.split("|", 1)
        front = parts[0].strip()
        back  = parts[1].strip()
        if not front or not back:
            await update.message.reply_text("❌ Both front and back must have text.")
            return
        if user_id not in all_cards:
            all_cards[user_id] = []
        all_cards[user_id].append({"front": front, "back": back})
        save_flashcards(all_cards)
        count = len(all_cards[user_id])
        await update.message.reply_text(
            f"✅ Flashcard added! You now have *{count}* card(s).\n\n"
            f"🟦 Front: *{front}*\n"
            f"🟩 Back: _{back}_\n\n"
            f"Start a quiz: `/flashcard quiz`",
            parse_mode="Markdown"
        )

    elif sub == "list":
        cards = all_cards.get(user_id, [])
        if not cards:
            await update.message.reply_text("📭 No flashcards yet. Add some with `/flashcard add`", parse_mode="Markdown")
            return
        lines = [f"🗂 *Your Flashcards ({len(cards)})*\n"]
        for i, c in enumerate(cards, 1):
            lines.append(f"*{i}.* 🟦 {c['front']}\n   🟩 _{c['back']}_\n")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif sub == "quiz":
        cards = all_cards.get(user_id, [])
        if not cards:
            await update.message.reply_text("📭 No cards to quiz! Add some: `/flashcard add Term | Definition`", parse_mode="Markdown")
            return
        shuffled = cards.copy()
        random.shuffle(shuffled)
        active_flashcard_sessions[user_id] = {"cards": shuffled, "idx": 0, "score": 0, "total": len(shuffled)}
        await _send_flashcard_question(update.message, user_id)

    elif sub == "clear":
        all_cards[user_id] = []
        save_flashcards(all_cards)
        await update.message.reply_text("🗑 All flashcards cleared!")

    else:
        await update.message.reply_text("❓ Unknown subcommand. Use: `add`, `list`, `quiz`, `clear`", parse_mode="Markdown")


async def _send_flashcard_question(message, user_id: str):
    session = active_flashcard_sessions.get(user_id)
    if not session:
        return
    idx   = session["idx"]
    total = session["total"]
    card  = session["cards"][idx]

    keyboard = [[
        InlineKeyboardButton("✅ I knew it!", callback_data=f"fc|correct|{user_id}"),
        InlineKeyboardButton("❌ I didn't", callback_data=f"fc|wrong|{user_id}"),
    ]]
    await message.reply_text(
        f"🗂 *Flashcard Quiz* — {idx+1}/{total}\n\n"
        f"🟦 *{card['front']}*\n\n"
        f"||{card['back']}||\n\n"
        f"_Tap to reveal, then mark yourself:_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def flashcard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("fc|"):
        return

    parts   = query.data.split("|")
    result  = parts[1]
    user_id = parts[2]

    session = active_flashcard_sessions.get(user_id)
    if not session:
        await query.edit_message_text("⏰ Quiz session expired. Start fresh: `/flashcard quiz`", parse_mode="Markdown")
        return

    if result == "correct":
        session["score"] += 1

    session["idx"] += 1

    if session["idx"] >= session["total"]:
        score = session["score"]
        total = session["total"]
        pct   = int(score / total * 100)
        grade = "🏆 Excellent!" if pct >= 80 else "👍 Good job!" if pct >= 60 else "📚 Keep studying!"
        del active_flashcard_sessions[user_id]
        await query.edit_message_text(
            f"🎉 *Quiz Complete!*\n\n"
            f"Score: *{score}/{total}* ({pct}%)\n"
            f"{grade}\n\n"
            f"Practice again: `/flashcard quiz`",
            parse_mode="Markdown"
        )
        return

    card    = session["cards"][session["idx"]]
    idx     = session["idx"]
    total   = session["total"]
    keyboard = [[
        InlineKeyboardButton("✅ I knew it!", callback_data=f"fc|correct|{user_id}"),
        InlineKeyboardButton("❌ I didn't", callback_data=f"fc|wrong|{user_id}"),
    ]]
    await query.edit_message_text(
        f"🗂 *Flashcard Quiz* — {idx+1}/{total}\n\n"
        f"🟦 *{card['front']}*\n\n"
        f"||{card['back']}||\n\n"
        f"_Tap to reveal, then mark yourself:_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ── /mcq ──────────────────────────────────────────────────

async def mcq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mcq <topic> — AI generates 3 fresh MCQ practice questions."""
    if not context.args:
        await update.message.reply_text(
            "📝 *MCQ Practice Generator*\n\n"
            "`/mcq Computer Networks`\n"
            "`/mcq DBMS basics`\n"
            "`/mcq Indian Constitution`\n"
            "`/mcq Photosynthesis`\n"
            "`/mcq Python OOP`\n\n"
            "_Every run gives DIFFERENT questions!_",
            parse_mode="Markdown"
        )
        return

    topic = " ".join(context.args)
    await update.message.chat.send_action("typing")

    # Random variety words so AI doesn't repeat the same questions
    variety = random.choice([
        "easy beginner", "intermediate", "advanced tricky", "application-based",
        "conceptual", "definition-based", "example-based", "numerical",
        "comparison-based", "real-world scenario"
    ])
    # Random chapter/subtopic hint to force diversity
    subtopic_hints = {
        "python": ["functions", "lists", "OOP", "modules", "exceptions", "file I/O", "decorators"],
        "dbms": ["SQL", "normalization", "transactions", "indexing", "ER diagrams", "joins"],
        "networks": ["OSI model", "TCP/IP", "routing", "DNS", "HTTP", "wireless", "security"],
        "physics": ["mechanics", "thermodynamics", "optics", "electricity", "magnetism", "waves"],
        "history": ["ancient", "medieval", "modern", "freedom struggle", "world wars", "civilizations"],
    }
    hint = ""
    for key, subtopics in subtopic_hints.items():
        if key in topic.lower():
            hint = f" Focus on: {random.choice(subtopics)}."
            break

    try:
        raw = _groq(
            system=(
                "You are an exam paper setter creating UNIQUE questions. "
                f"Generate exactly 3 {variety} multiple choice questions on the given topic.{hint} "
                "IMPORTANT: Generate DIFFERENT questions each time — vary the subtopics and difficulty. "
                "Each question must have 4 options (A, B, C, D) and one correct answer.\n"
                "Format EXACTLY like this:\n"
                "Q1: <question>\n"
                "A: <option>\nB: <option>\nC: <option>\nD: <option>\n"
                "Ans: <A/B/C/D>\n\n"
                "Q2: <different question>\n"
                "A: <option>\nB: <option>\nC: <option>\nD: <option>\n"
                "Ans: <A/B/C/D>\n\n"
                "Q3: <another different question>\n"
                "A: <option>\nB: <option>\nC: <option>\nD: <option>\n"
                "Ans: <A/B/C/D>"
            ),
            user=f"Topic: {topic}. Make the questions unique and not repetitive.",
            max_tokens=700,
            temp=0.95,   # HIGH temperature = more variety every run
        )

        await update.message.reply_text(
            f"📝 MCQ Practice: {topic.title()} ({variety})\n\n"
            f"{raw}\n\n"
            f"Want more questions? Run /mcq {topic} again — you'll get different ones!",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ MCQ generator error: {str(e)[:80]}\nTry again!")


# ── /essay ────────────────────────────────────────────────

async def essay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/essay <topic> — AI generates a detailed essay outline."""
    if not context.args:
        await update.message.reply_text(
            "✍️ *Essay Outline Generator*\n\n"
            "`/essay Climate Change`\n"
            "`/essay Role of Technology in Education`\n"
            "`/essay Digital India`\n"
            "`/essay Impact of Social Media`\n"
            "`/essay Artificial Intelligence pros and cons`",
            parse_mode="Markdown"
        )
        return

    topic = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        outline = _groq(
            system=(
                "You are an expert academic writing tutor. "
                "Create a detailed essay outline for the given topic.\n"
                "Format:\n"
                "📌 *Introduction* — Hook + thesis statement (2-3 points)\n"
                "📌 *Body Para 1* — Main argument + supporting evidence\n"
                "📌 *Body Para 2* — Second argument + examples\n"
                "📌 *Body Para 3* — Counter-argument + rebuttal\n"
                "📌 *Conclusion* — Summary + call to action\n"
                "📌 *Key Points to Remember* — 3 important facts\n\n"
                "Keep each section to 2-3 bullet points. Make it useful for a student."
            ),
            user=f"Essay topic: {topic}",
            max_tokens=550,
            temp=0.5,
        )

        await update.message.reply_text(
            f"✍️ *Essay Outline: {topic.title()}*\n\n{outline}",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Essay generator unavailable. Try again!")


# ── /formula ─────────────────────────────────────────────

FORMULA_SHEETS = {
    "physics": (
        "⚛️ *Physics Formulas*\n\n"
        "🔵 *Mechanics*\n"
        "• v = u + at\n"
        "• s = ut + ½at²\n"
        "• v² = u² + 2as\n"
        "• F = ma\n"
        "• KE = ½mv²\n"
        "• PE = mgh\n"
        "• p = mv (momentum)\n\n"
        "🔵 *Waves & Light*\n"
        "• v = fλ (wave speed)\n"
        "• n = c/v (refractive index)\n"
        "• 1/f = 1/v - 1/u (lens)\n\n"
        "🔵 *Electricity*\n"
        "• V = IR (Ohm's Law)\n"
        "• P = VI = I²R = V²/R\n"
        "• Q = CV (capacitor)\n\n"
        "🔵 *Thermodynamics*\n"
        "• Q = mcΔT (heat)\n"
        "• PV = nRT (ideal gas)\n"
    ),
    "math": (
        "📐 *Mathematics Formulas*\n\n"
        "🔵 *Algebra*\n"
        "• (a+b)² = a²+2ab+b²\n"
        "• (a-b)² = a²-2ab+b²\n"
        "• (a+b)(a-b) = a²-b²\n"
        "• Quadratic: x = (-b±√(b²-4ac))/2a\n\n"
        "🔵 *Geometry*\n"
        "• Circle Area = πr²\n"
        "• Circle Circumference = 2πr\n"
        "• Sphere Volume = (4/3)πr³\n"
        "• Triangle Area = ½bh\n"
        "• Pythagorean: a²+b²=c²\n\n"
        "🔵 *Trigonometry*\n"
        "• sin²θ + cos²θ = 1\n"
        "• sin(A+B) = sinAcosB + cosAsinB\n"
        "• SOHCAHTOA rule\n\n"
        "🔵 *Statistics*\n"
        "• Mean = Σx/n\n"
        "• Variance = Σ(x-μ)²/n\n"
        "• SD = √Variance\n"
    ),
    "chemistry": (
        "⚗️ *Chemistry Formulas*\n\n"
        "🔵 *Mole Concept*\n"
        "• n = m/M (moles)\n"
        "• 1 mole = 6.022×10²³ (Avogadro)\n"
        "• PV = nRT (ideal gas)\n\n"
        "🔵 *Solutions*\n"
        "• Molarity (M) = moles/litre\n"
        "• Molality (m) = moles/kg solvent\n"
        "• Normality = Equivalents/litre\n\n"
        "🔵 *Electrochemistry*\n"
        "• E°cell = E°cathode - E°anode\n"
        "• ΔG = -nFE\n"
        "• Q = It (charge)\n\n"
        "🔵 *Thermodynamics*\n"
        "• ΔG = ΔH - TΔS\n"
        "• ΔH = Σ(products) - Σ(reactants)\n"
    ),
    "cs": (
        "💻 *Computer Science Formulas & Concepts*\n\n"
        "🔵 *Time Complexity*\n"
        "• O(1) Constant, O(log n) Binary Search\n"
        "• O(n) Linear, O(n log n) Merge Sort\n"
        "• O(n²) Bubble/Selection/Insertion Sort\n"
        "• O(2ⁿ) Exponential (recursive)\n\n"
        "🔵 *Number Systems*\n"
        "• Binary → Decimal: sum of (bit × 2^position)\n"
        "• Hex digits: 0-9, A=10, B=11...F=15\n"
        "• 1 Byte = 8 bits\n"
        "• 1 KB = 1024 Bytes\n\n"
        "🔵 *Boolean Algebra*\n"
        "• A AND 0 = 0, A OR 1 = 1\n"
        "• De Morgan: ¬(A∧B) = ¬A∨¬B\n"
        "• XOR: A⊕A = 0, A⊕0 = A\n\n"
        "🔵 *Database*\n"
        "• Normalization: 1NF→2NF→3NF→BCNF\n"
        "• ACID: Atomicity, Consistency, Isolation, Durability\n"
    ),
    "economics": (
        "📈 *Economics Formulas*\n\n"
        "🔵 *Micro*\n"
        "• PED = % ΔQd / % ΔP\n"
        "• TR = P × Q\n"
        "• MR = ΔTR/ΔQ\n"
        "• Profit = TR - TC\n\n"
        "🔵 *Macro*\n"
        "• GDP = C + I + G + (X-M)\n"
        "• GDP Deflator = (Nominal/Real GDP) × 100\n"
        "• Inflation Rate = ((CPI2-CPI1)/CPI1) × 100\n"
        "• Money Multiplier = 1/Reserve Ratio\n\n"
        "🔵 *Banking*\n"
        "• Simple Interest = PRT/100\n"
        "• Compound Interest = P(1+r/n)^(nt) - P\n"
    ),
}


async def formula_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/formula <subject> — Quick formula reference sheet."""
    if not context.args:
        subjects = " · ".join(f"`{k}`" for k in FORMULA_SHEETS)
        await update.message.reply_text(
            f"📐 *Formula Reference*\n\n"
            f"Available subjects:\n{subjects}\n\n"
            f"Example: `/formula math`\n"
            f"Or: `/formula physics`",
            parse_mode="Markdown"
        )
        return

    subject = context.args[0].lower()

    # Aliases
    aliases = {
        "maths": "math", "mathematics": "math",
        "phy": "physics", "phys": "physics",
        "chem": "chemistry",
        "computer": "cs", "programming": "cs", "bca": "cs",
        "eco": "economics", "econ": "economics",
    }
    subject = aliases.get(subject, subject)

    if subject not in FORMULA_SHEETS:
        subjects = ", ".join(FORMULA_SHEETS.keys())
        await update.message.reply_text(
            f"❌ Subject `{subject}` not found.\n\n"
            f"Available: {subjects}",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(FORMULA_SHEETS[subject], parse_mode="Markdown")
