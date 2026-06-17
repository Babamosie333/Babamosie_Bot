# ============================================================
#  handlers/ai_advanced.py
#  /memory — Show/clear AI memory
#  /summarizeurl <url> — Summarize any article URL
#  /rewrite <text> — Rewrite in different styles
#  /grammar <text> — Fix grammar with explanations
#  /ask <question> — AI with web context
# ============================================================

import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── Persistent AI memory per user ─────────────────────────
# Stored as: { user_id: [ {"role": "user"/"assistant", "content": "..."} ] }
# This is the LONG-TERM memory that survives across conversations
# (Short-term context is already in ai.py's conversation_history)
ai_memory: dict[str, list] = {}
MAX_MEMORY_ITEMS = 20  # Max facts to remember per user


def _groq(messages: list, max_tokens: int = 500, temp: float = 0.7) -> str:
    resp = requests.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temp},
        timeout=25,
    )
    return resp.json()["choices"][0]["message"]["content"].strip()


def _groq_simple(system: str, user: str, max_tokens: int = 500, temp: float = 0.7) -> str:
    return _groq([{"role": "system", "content": system}, {"role": "user", "content": user}], max_tokens, temp)


# ── /memory ───────────────────────────────────────────────

def get_user_memory_context(user_id: str) -> str:
    """Returns formatted memory string to inject into AI prompts."""
    facts = ai_memory.get(user_id, [])
    if not facts:
        return ""
    return "What you remember about this user:\n" + "\n".join(f"- {f}" for f in facts)


def update_memory_from_conversation(user_id: str, user_msg: str, ai_reply: str):
    """
    Automatically extract and store important facts from conversations.
    Called after every AI reply.
    """
    if user_id not in ai_memory:
        ai_memory[user_id] = []

    # Ask AI to extract any important personal facts from this exchange
    try:
        extraction = _groq_simple(
            system=(
                "You are a memory extractor. From the conversation below, extract any personal facts "
                "worth remembering about the user (name, college, city, interests, goals, problems they mentioned). "
                "Return ONLY a JSON array of short strings, or an empty array [] if nothing important. "
                "Example: [\"Studies BCA at XYZ college\", \"Likes Python\", \"Lives in Kanpur\"]\n"
                "Return ONLY the JSON array, nothing else."
            ),
            user=f"User said: {user_msg}\nAI replied: {ai_reply[:300]}",
            max_tokens=150,
            temp=0.1,
        )
        # Parse JSON array
        import json
        facts = json.loads(extraction.strip())
        if isinstance(facts, list):
            for fact in facts:
                if fact and fact not in ai_memory[user_id]:
                    ai_memory[user_id].append(str(fact))
            # Keep only last MAX_MEMORY_ITEMS facts
            ai_memory[user_id] = ai_memory[user_id][-MAX_MEMORY_ITEMS:]
    except Exception:
        pass  # Memory extraction is best-effort, never block main flow


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/memory — View or clear what the bot remembers about you."""
    user_id = str(update.effective_user.id)

    if context.args and context.args[0].lower() == "clear":
        ai_memory[user_id] = []
        await update.message.reply_text(
            "🧹 *Memory cleared!*\n\nI've forgotten everything about you. Fresh start! 🌱",
            parse_mode="Markdown"
        )
        return

    facts = ai_memory.get(user_id, [])
    if not facts:
        await update.message.reply_text(
            "🧠 *My Memory About You*\n\n"
            "I don't remember anything specific yet.\n"
            "Chat with me more and I'll start learning about you!\n\n"
            "Use `/memory clear` to wipe my memory anytime.",
            parse_mode="Markdown"
        )
        return

    lines = ["🧠 *What I Remember About You*\n"]
    for i, fact in enumerate(facts, 1):
        lines.append(f"{i}. {fact}")
    lines.append(f"\n_Total: {len(facts)} memory items_")
    lines.append("Use `/memory clear` to forget everything.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /summarizeurl ─────────────────────────────────────────

def _extract_text_from_url(url: str) -> str:
    """Fetch a URL and extract readable text content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    resp    = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
    html    = resp.text

    # Strip HTML tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>',  '', text,  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>',                  ' ', text)
    text = re.sub(r'&[a-z]+;',                 ' ', text)
    text = re.sub(r'\s+',                       ' ', text).strip()

    # Return first 3000 chars (enough for AI to summarize)
    return text[:3000]


async def summarizeurl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/summarizeurl <url> — Fetch and summarize any article or webpage."""
    if not context.args:
        await update.message.reply_text(
            "🔗 *Article Summarizer*\n\n"
            "`/summarizeurl https://example.com/article`\n\n"
            "Works with:\n"
            "• News articles\n"
            "• Wikipedia pages\n"
            "• Blog posts\n"
            "• Documentation pages",
            parse_mode="Markdown"
        )
        return

    url = context.args[0]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    await update.message.chat.send_action("typing")
    msg = await update.message.reply_text("🔍 Fetching article...")

    try:
        text = _extract_text_from_url(url)

        if len(text) < 100:
            await msg.edit_text("❌ Couldn't extract readable content from that URL. Try a different link.")
            return

        await msg.edit_text("🤖 Summarizing with AI...")

        summary = _groq_simple(
            system=(
                "You are an expert article summarizer. Summarize the given webpage content.\n"
                "Format:\n"
                "📌 *Topic:* <one line>\n"
                "📝 *Summary:* <3-5 sentences covering main points>\n"
                "🔑 *Key Points:*\n• point 1\n• point 2\n• point 3\n"
                "💡 *Takeaway:* <one actionable sentence>\n\n"
                "Be concise and accurate. Ignore ads and navigation text."
            ),
            user=f"Webpage content:\n{text}",
            max_tokens=400,
            temp=0.3,
        )

        domain = url.split("//")[-1].split("/")[0]
        await msg.edit_text(
            f"🔗 *Summary: {domain}*\n\n{summary}\n\n_Source: {url[:60]}..._" if len(url) > 60
            else f"🔗 *Summary: {domain}*\n\n{summary}\n\n_Source: {url}_",
            parse_mode="Markdown"
        )

    except requests.Timeout:
        await msg.edit_text("❌ URL took too long to load. Try a different link.")
    except Exception as e:
        await msg.edit_text(f"❌ Could not summarize that URL.\nError: {str(e)[:80]}")


# ── /rewrite ──────────────────────────────────────────────

REWRITE_STYLES = {
    "formal":       "Rewrite this text in a formal, professional tone suitable for official emails or reports.",
    "casual":       "Rewrite this text in a casual, friendly tone like texting a friend.",
    "simple":       "Rewrite this text in very simple language a 10-year-old can understand.",
    "professional": "Rewrite this text in a polished professional style suitable for LinkedIn or a cover letter.",
    "funny":        "Rewrite this text in a humorous, witty style with appropriate jokes.",
    "persuasive":   "Rewrite this text as a persuasive argument that convinces the reader.",
    "academic":     "Rewrite this text in a formal academic style with sophisticated vocabulary.",
    "hindi":        "Rewrite this text in simple Hindi (Devanagari script).",
    "shorter":      "Rewrite this text making it much shorter and more concise while keeping all key info.",
    "longer":       "Expand this text with more detail, examples, and explanation.",
}


async def rewrite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/rewrite <style> | <text> — Rewrite text in different styles."""
    if not context.args:
        styles = "\n".join(f"• `{k}` — {v[:50]}..." for k, v in REWRITE_STYLES.items())
        await update.message.reply_text(
            f"✍️ *Text Rewriter*\n\n"
            f"Usage: `/rewrite <style> | <your text>`\n\n"
            f"Available styles:\n{styles}\n\n"
            f"Example:\n`/rewrite formal | hey bro can u send the report`",
            parse_mode="Markdown"
        )
        return

    full = " ".join(context.args)
    if "|" not in full:
        await update.message.reply_text(
            "❌ Use `|` to separate style from text.\n"
            "Example: `/rewrite casual | Please find attached the requested document.`",
            parse_mode="Markdown"
        )
        return

    parts = full.split("|", 1)
    style = parts[0].strip().lower()
    text  = parts[1].strip()

    if style not in REWRITE_STYLES:
        await update.message.reply_text(
            f"❌ Unknown style: `{style}`\n\n"
            f"Available: {', '.join(REWRITE_STYLES.keys())}",
            parse_mode="Markdown"
        )
        return

    await update.message.chat.send_action("typing")

    try:
        instruction = REWRITE_STYLES[style]
        rewritten   = _groq_simple(
            system=f"You are an expert writer. {instruction} Return ONLY the rewritten text, nothing else.",
            user=text,
            max_tokens=400,
            temp=0.7,
        )

        # Build style buttons for quick switching
        other_styles = [s for s in list(REWRITE_STYLES.keys())[:6] if s != style]
        btn_rows = [
            [InlineKeyboardButton(s.title(), callback_data=f"rw|{s}|{text[:100]}") for s in other_styles[:3]],
            [InlineKeyboardButton(s.title(), callback_data=f"rw|{s}|{text[:100]}") for s in other_styles[3:6]],
        ]

        await update.message.reply_text(
            f"✍️ *Rewritten ({style.title()} style)*\n\n"
            f"*Original:*\n_{text[:200]}_\n\n"
            f"*Rewritten:*\n{rewritten}",
            reply_markup=InlineKeyboardMarkup(btn_rows),
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Rewrite failed: {str(e)[:80]}")


async def rewrite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rewrite style button taps."""
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("rw|"):
        return

    parts = query.data.split("|", 2)
    style = parts[1]
    text  = parts[2] if len(parts) > 2 else ""

    if not text or style not in REWRITE_STYLES:
        await query.answer("Expired. Use /rewrite again.", show_alert=True)
        return

    try:
        instruction = REWRITE_STYLES[style]
        rewritten   = _groq_simple(
            system=f"You are an expert writer. {instruction} Return ONLY the rewritten text.",
            user=text,
            max_tokens=400,
            temp=0.7,
        )
        await query.message.reply_text(
            f"✍️ *Rewritten ({style.title()} style)*\n\n{rewritten}",
            parse_mode="Markdown"
        )
    except Exception:
        await query.answer("Failed. Try again.", show_alert=True)


# ── /grammar ──────────────────────────────────────────────

async def grammar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/grammar <text> — Fix grammar and explain mistakes."""
    if not context.args:
        await update.message.reply_text(
            "📝 *Grammar Checker*\n\n"
            "`/grammar I goes to college yesterday`\n"
            "`/grammar She don't know the answer`\n"
            "`/grammar He is more faster than me`\n\n"
            "I'll fix it AND explain what was wrong!",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        result = _groq_simple(
            system=(
                "You are an expert English grammar teacher. Analyze the given text.\n"
                "Format your response EXACTLY like this:\n"
                "✅ *Corrected:* <corrected text>\n\n"
                "📋 *Mistakes Found:*\n"
                "1. <original wrong phrase> → <correct phrase>: <brief explanation>\n"
                "2. (if more mistakes)\n\n"
                "💡 *Tip:* <one grammar rule to remember>\n\n"
                "If the text is already correct, say so and give a tip anyway."
            ),
            user=f"Check this text: {text}",
            max_tokens=400,
            temp=0.2,
        )

        await update.message.reply_text(
            f"📝 *Grammar Check*\n\n"
            f"*Your text:* _{text}_\n\n"
            f"{result}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Grammar checker unavailable: {str(e)[:80]}")


# ── /ask (AI + web context) ───────────────────────────────

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ask <question> — AI answers with awareness of recent events context."""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Smart Ask*\n\n"
            "Ask anything — I'll answer with my full knowledge + your memory context!\n\n"
            "`/ask What is the latest Python version?`\n"
            "`/ask How do I get a job as a fresher in India?`\n"
            "`/ask Explain JWT tokens simply`\n\n"
            "_Also just type any message to chat with AI!_",
            parse_mode="Markdown"
        )
        return

    question = " ".join(context.args)
    user_id  = str(update.effective_user.id)
    await update.message.chat.send_action("typing")

    # Inject user memory into system prompt for personalized answers
    memory_ctx = get_user_memory_context(user_id)

    try:
        system = (
            "You are Jarvis, a smart AI assistant for a BCA student in India. "
            "Answer questions clearly, concisely, and helpfully. "
            "Use simple language, code examples where relevant. "
            "For current events you're unsure about, say so honestly. "
        )
        if memory_ctx:
            system += f"\n\n{memory_ctx}"

        answer = _groq_simple(system=system, user=question, max_tokens=600, temp=0.6)

        # Update memory based on this exchange
        update_memory_from_conversation(user_id, question, answer)

        await update.message.reply_text(f"🤖 {answer}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ask failed: {str(e)[:80]}")
