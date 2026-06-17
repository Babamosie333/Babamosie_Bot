# ============================================================
#  handlers/productivity.py
#  /todo — To-do list manager
#  /calc — Expression calculator
#  /countdown <date> — Days until event
#  /pomodoro — Pomodoro timer
# ============================================================

import asyncio
import json
import os
import re
import math
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

TODO_FILE = "todo_db.json"


# ── To-Do List ────────────────────────────────────────────

def _load_todos() -> dict:
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE) as f:
            return json.load(f)
    return {}


def _save_todos(data: dict):
    with open(TODO_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /todo add <task>    — Add a task
    /todo done <num>    — Mark task done
    /todo del <num>     — Delete a task
    /todo list          — Show all tasks
    /todo clear         — Clear all tasks
    """
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(
            "📋 *To-Do List Commands:*\n\n"
            "`/todo add Buy groceries` — Add task\n"
            "`/todo list` — View all tasks\n"
            "`/todo done 1` — Mark task 1 done ✅\n"
            "`/todo del 2` — Delete task 2\n"
            "`/todo clear` — Clear all tasks",
            parse_mode="Markdown"
        )
        return

    sub = context.args[0].lower()
    todos = _load_todos()
    if user_id not in todos:
        todos[user_id] = []

    tasks = todos[user_id]

    if sub == "add":
        if len(context.args) < 2:
            await update.message.reply_text("❌ Usage: `/todo add <task>`", parse_mode="Markdown")
            return
        task_text = " ".join(context.args[1:])
        tasks.append({"text": task_text, "done": False, "added": datetime.now().strftime("%d %b")})
        _save_todos(todos)
        await update.message.reply_text(f"✅ Task added! #{len(tasks)}: *{task_text}*", parse_mode="Markdown")

    elif sub == "list":
        if not tasks:
            await update.message.reply_text("📋 Your to-do list is empty!\nAdd tasks with `/todo add <task>`", parse_mode="Markdown")
            return
        lines = ["📋 *Your To-Do List*\n"]
        for i, t in enumerate(tasks, 1):
            icon = "✅" if t["done"] else "⬜"
            text = f"~{t['text']}~" if t["done"] else t["text"]
            lines.append(f"{i}. {icon} {text} _{t.get('added', '')}_")
        pending = sum(1 for t in tasks if not t["done"])
        lines.append(f"\n📊 {pending}/{len(tasks)} pending")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif sub == "done":
        if len(context.args) < 2 or not context.args[1].isdigit():
            await update.message.reply_text("❌ Usage: `/todo done <number>`", parse_mode="Markdown")
            return
        idx = int(context.args[1]) - 1
        if idx < 0 or idx >= len(tasks):
            await update.message.reply_text(f"❌ No task #{idx+1}. You have {len(tasks)} tasks.")
            return
        tasks[idx]["done"] = True
        _save_todos(todos)
        await update.message.reply_text(f"✅ Task #{idx+1} marked done!\n~{tasks[idx]['text']}~", parse_mode="Markdown")

    elif sub == "del":
        if len(context.args) < 2 or not context.args[1].isdigit():
            await update.message.reply_text("❌ Usage: `/todo del <number>`", parse_mode="Markdown")
            return
        idx = int(context.args[1]) - 1
        if idx < 0 or idx >= len(tasks):
            await update.message.reply_text(f"❌ No task #{idx+1}.")
            return
        removed = tasks.pop(idx)
        _save_todos(todos)
        await update.message.reply_text(f"🗑 Deleted: *{removed['text']}*", parse_mode="Markdown")

    elif sub == "clear":
        todos[user_id] = []
        _save_todos(todos)
        await update.message.reply_text("🗑 All tasks cleared!")

    else:
        await update.message.reply_text(
            "❓ Unknown subcommand. Use: `add`, `list`, `done`, `del`, `clear`",
            parse_mode="Markdown"
        )


# ── Calculator ────────────────────────────────────────────

def _safe_eval(expr: str) -> str:
    """Safely evaluate a math expression."""
    # Allow only safe characters
    allowed = re.compile(r'^[\d\s\+\-\*\/\%\(\)\.\^sqrt|sin|cos|tan|log|pi|e]+$')
    clean = expr.replace("^", "**").replace("√", "sqrt(").strip()

    # Replace math functions
    safe_dict = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log10, "ln": math.log,
        "pi": math.pi, "e": math.e, "abs": abs, "round": round,
    }

    # Strip dangerous chars
    safe_expr = re.sub(r'[^0-9\s\+\-\*\/\%\(\)\.\,sqrt|sin|cos|tan|log|ln|pi|e|abs|round]', '', clean)
    result = eval(safe_expr, {"__builtins__": {}}, safe_dict)
    return result


async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/calc <expression> — Safe math calculator."""
    if not context.args:
        await update.message.reply_text(
            "🧮 *Calculator*\n\n"
            "`/calc 2 + 2 * 10`\n"
            "`/calc (100 / 4) * 3`\n"
            "`/calc sqrt(144)`\n"
            "`/calc sin(30)`\n"
            "`/calc 2 ^ 8` (power)\n"
            "`/calc pi * 5 ^ 2` (circle area)",
            parse_mode="Markdown"
        )
        return

    expr = " ".join(context.args)
    try:
        result = _safe_eval(expr)
        if isinstance(result, float):
            # Clean display
            result_str = f"{result:.10g}"
        else:
            result_str = str(result)
        await update.message.reply_text(
            f"🧮 *Calculator*\n\n"
            f"`{expr}`\n\n"
            f"= *{result_str}*",
            parse_mode="Markdown"
        )
    except ZeroDivisionError:
        await update.message.reply_text("❌ Cannot divide by zero!")
    except Exception:
        await update.message.reply_text(
            f"❌ Invalid expression: `{expr}`\n\n"
            "Try: `/calc 2 + 2` or `/calc sqrt(16)`",
            parse_mode="Markdown"
        )


# ── Countdown ─────────────────────────────────────────────

async def countdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/countdown <DD-MM-YYYY> <event name> — Days until an event."""
    if not context.args:
        await update.message.reply_text(
            "⏳ *Countdown Timer*\n\n"
            "`/countdown 31-12-2025 New Year`\n"
            "`/countdown 15-08-2025 Independence Day`\n"
            "`/countdown 25-12-2025 Christmas`\n\n"
            "Format: `DD-MM-YYYY`",
            parse_mode="Markdown"
        )
        return

    date_str  = context.args[0]
    event     = " ".join(context.args[1:]) if len(context.args) > 1 else "Your Event"

    try:
        target = datetime.strptime(date_str, "%d-%m-%Y").date()
        today  = date.today()
        delta  = (target - today).days

        if delta < 0:
            await update.message.reply_text(
                f"⏳ *{event}* was *{abs(delta)} days ago!* 📅\n"
                f"Date: {target.strftime('%d %B %Y')}",
                parse_mode="Markdown"
            )
        elif delta == 0:
            await update.message.reply_text(
                f"🎉 *{event}* is *TODAY!* 🎊",
                parse_mode="Markdown"
            )
        else:
            weeks = delta // 7
            days  = delta % 7
            extra = f" ({weeks} weeks, {days} days)" if weeks > 0 else ""
            await update.message.reply_text(
                f"⏳ *Countdown: {event}*\n\n"
                f"📅 Date: {target.strftime('%d %B %Y')}\n"
                f"⏰ *{delta} days remaining*{extra}\n\n"
                f"_Today: {today.strftime('%d %B %Y')}_",
                parse_mode="Markdown"
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid date format!\n"
            "Use DD-MM-YYYY\nExample: `/countdown 25-12-2025 Christmas`",
            parse_mode="Markdown"
        )


# ── Pomodoro Timer ────────────────────────────────────────

async def pomodoro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pomodoro [minutes] — Start a Pomodoro focus timer."""
    minutes = 25  # Default pomodoro
    break_min = 5

    if context.args:
        try:
            minutes = int(context.args[0])
            minutes = max(1, min(60, minutes))  # clamp 1-60
        except ValueError:
            pass

    chat_id = update.effective_chat.id
    seconds = minutes * 60

    await update.message.reply_text(
        f"🍅 *Pomodoro Started!*\n\n"
        f"⏱ Focus time: *{minutes} minutes*\n"
        f"☕ Break after: {break_min} minutes\n\n"
        f"_Put your phone down and focus!_ 💪\n"
        f"I'll ping you when time's up!",
        parse_mode="Markdown"
    )

    async def send_done():
        await asyncio.sleep(seconds)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔔 *Pomodoro Complete!* 🎉\n\n"
                f"✅ {minutes} minutes of focused work done!\n"
                f"☕ Now take a {break_min}-minute break.\n\n"
                f"_Start another? /pomodoro {minutes}_"
            ),
            parse_mode="Markdown"
        )

    asyncio.create_task(send_done())
