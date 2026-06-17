# ============================================================
#  handlers/student_advanced.py
#  /syllabus <course> <semester> — AI topic list
#  /pyq <subject>               — Previous year questions
#  /studyplan <exam> <days>     — Day-by-day study schedule
#  /doubt <question>            — Detailed explanation
#  /codereview                  — Code review (reply to code)
# ============================================================

import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


def _groq(system: str, user: str, max_tokens: int = 700, temp: float = 0.5) -> str:
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


# ── /syllabus ─────────────────────────────────────────────

async def syllabus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/syllabus <course> <semester> — AI generates topic list for any exam."""
    if not context.args:
        await update.message.reply_text(
            "📚 *Syllabus Generator*\n\n"
            "`/syllabus BCA 3` — BCA Semester 3\n"
            "`/syllabus MCA 1` — MCA Semester 1\n"
            "`/syllabus BSc CS 4` — BSc CS Semester 4\n"
            "`/syllabus Class 12 Physics`\n"
            "`/syllabus GATE CS`\n\n"
            "_Generates likely topics based on standard Indian university curricula._",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        result = _groq(
            system=(
                "You are an expert Indian university curriculum advisor. "
                "Generate a comprehensive syllabus/topic list for the given course and semester. "
                "Format:\n"
                "📚 *[Course Name]*\n\n"
                "For each subject include:\n"
                "📖 *Subject Name*\n"
                "• Topic 1\n• Topic 2\n• Topic 3...\n\n"
                "Cover 4-6 subjects typically found in Indian universities. "
                "Focus on BCA/MCA/BSc CS standard curricula if applicable. "
                "Be specific with topic names."
            ),
            user=f"Generate syllabus for: {query}",
            max_tokens=700,
        )
        await update.message.reply_text(
            f"📚 *Syllabus: {query}*\n\n{result}\n\n"
            f"_⚠️ Verify with your actual university syllabus._",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:80]}")


# ── /pyq ──────────────────────────────────────────────────

async def pyq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pyq <subject> — AI generates likely previous year questions."""
    if not context.args:
        await update.message.reply_text(
            "📋 *Previous Year Questions*\n\n"
            "`/pyq DBMS`\n"
            "`/pyq Operating System`\n"
            "`/pyq Data Structures`\n"
            "`/pyq Computer Networks`\n"
            "`/pyq Python Programming`\n\n"
            "_AI generates likely exam questions based on standard patterns._",
            parse_mode="Markdown"
        )
        return

    subject = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        result = _groq(
            system=(
                "You are an expert at predicting Indian university exam questions. "
                "Generate 10 likely previous year exam questions for the given subject. "
                "Mix of: 2-mark questions (short answer), 5-mark questions (medium), "
                "and 10-mark questions (long answer/essay). "
                "Format:\n"
                "✏️ *2-Mark Questions:*\n1. ...\n2. ...\n\n"
                "📝 *5-Mark Questions:*\n1. ...\n2. ...\n\n"
                "📄 *10-Mark Questions:*\n1. ...\n2. ...\n\n"
                "Make questions realistic and exam-style."
            ),
            user=f"Subject: {subject}",
            max_tokens=650,
            temp=0.7,
        )
        await update.message.reply_text(
            f"📋 *PYQ Pattern: {subject}*\n\n{result}\n\n"
            f"_Practice these! Similar questions often appear in exams._",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:80]}")


# ── /studyplan ────────────────────────────────────────────

async def studyplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/studyplan <exam/subject> <days> — AI builds a day-by-day study schedule."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "📅 *Study Plan Generator*\n\n"
            "`/studyplan DBMS 7` — 7-day DBMS plan\n"
            "`/studyplan BCA Semester 3 30` — 30-day full semester plan\n"
            "`/studyplan Python basics 14` — 2-week Python plan\n"
            "`/studyplan GATE CS 90` — 3-month GATE plan\n\n"
            "Format: `/studyplan <topic> <number of days>`",
            parse_mode="Markdown"
        )
        return

    # Last arg is days, rest is topic
    try:
        days  = int(context.args[-1])
        topic = " ".join(context.args[:-1])
    except ValueError:
        topic = " ".join(context.args)
        days  = 7

    days = max(1, min(days, 90))  # Clamp 1-90 days
    await update.message.chat.send_action("typing")

    try:
        result = _groq(
            system=(
                "You are an expert study planner for Indian university students. "
                f"Create a realistic {days}-day study plan for the given topic. "
                "Format as a day-by-day schedule. For each day specify:\n"
                "📅 *Day X:* Topic to cover + specific chapters/subtopics\n"
                "⏱ Suggested hours\n"
                "📝 Quick revision tip\n\n"
                "Group related topics together. Include revision days for longer plans. "
                "Keep it practical and achievable for a student."
            ),
            user=f"Topic: {topic}, Duration: {days} days",
            max_tokens=700,
            temp=0.5,
        )
        await update.message.reply_text(
            f"📅 *{days}-Day Study Plan: {topic}*\n\n{result}\n\n"
            f"💪 _Stick to the plan! Consistency beats intensity._",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:80]}")


# ── /doubt ────────────────────────────────────────────────

async def doubt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/doubt <question> — Detailed explanation with examples."""
    if not context.args:
        await update.message.reply_text(
            "🤔 *Doubt Solver*\n\n"
            "Ask any technical or academic doubt!\n\n"
            "`/doubt What is the difference between stack and queue?`\n"
            "`/doubt How does TCP handshake work?`\n"
            "`/doubt What is normalization in DBMS?`\n"
            "`/doubt Explain recursion with example`\n\n"
            "_I give detailed answers with examples!_",
            parse_mode="Markdown"
        )
        return

    question = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        result = _groq(
            system=(
                "You are an expert tutor for BCA/MCA/CS students in India. "
                "Answer the doubt with a detailed, clear explanation. "
                "Format:\n"
                "💡 *Simple Answer:* (1-2 sentences)\n\n"
                "📖 *Detailed Explanation:*\n(step by step with concepts)\n\n"
                "💻 *Example:*\n(code or real-world example)\n\n"
                "🔑 *Key Points to Remember:*\n• point 1\n• point 2\n\n"
                "Use simple language. Add code blocks where helpful."
            ),
            user=f"Doubt: {question}",
            max_tokens=650,
            temp=0.4,
        )
        await update.message.reply_text(
            f"🤔 *Doubt: {question[:50]}...*\n\n{result}" if len(question) > 50
            else f"🤔 *Doubt: {question}*\n\n{result}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:80]}")


# ── /codereview ───────────────────────────────────────────

async def codereview_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/codereview — Reply to a message containing code to get a review."""
    # Check if it's a reply to code
    code = None
    if update.message.reply_to_message and update.message.reply_to_message.text:
        code = update.message.reply_to_message.text
    elif context.args:
        code = " ".join(context.args)

    if not code:
        await update.message.reply_text(
            "💻 *Code Reviewer*\n\n"
            "Two ways to use:\n\n"
            "1️⃣ *Reply to a code message:*\n"
            "   Send your code → reply to it with `/codereview`\n\n"
            "2️⃣ *Paste code directly:*\n"
            "   `/codereview def hello(): print('hi')`\n\n"
            "_I'll check for bugs, improvements, and best practices!_",
            parse_mode="Markdown"
        )
        return

    await update.message.chat.send_action("typing")

    try:
        result = _groq(
            system=(
                "You are a senior software engineer doing a code review. "
                "Analyze the given code and provide feedback. Format:\n"
                "✅ *What's Good:*\n• (positive points)\n\n"
                "🐛 *Bugs/Issues Found:*\n• (if any, or 'None found')\n\n"
                "💡 *Improvements:*\n• improvement 1\n• improvement 2\n\n"
                "📝 *Improved Code:*\n```\n(rewritten better version)\n```\n\n"
                "🎯 *Overall Rating:* X/10\n\n"
                "Be constructive and educational."
            ),
            user=f"Review this code:\n\n{code}",
            max_tokens=650,
            temp=0.3,
        )
        await update.message.reply_text(
            f"💻 *Code Review*\n\n{result}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Code review failed: {str(e)[:80]}")
