# ============================================================
#  handlers/reminder.py
#  /remind <time> <message>
#  Examples:
#    /remind 10m Call mom
#    /remind 2h Submit assignment
#    /remind 1d Wake up early
# ============================================================

import asyncio
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

# Stores active reminders: list of dicts
# { user_id, chat_id, message, fire_at }
active_reminders: list[dict] = []


def parse_time(time_str: str) -> int | None:
    """
    Convert time string to seconds.
    10s → 10, 5m → 300, 2h → 7200, 1d → 86400
    Returns None if invalid format.
    """
    match = re.fullmatch(r"(\d+)(s|m|h|d)", time_str.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return value * multipliers[unit]


async def remind_after(seconds: int, chat_id: int, message: str, context: ContextTypes.DEFAULT_TYPE):
    """Background coroutine — sleeps then sends the reminder."""
    await asyncio.sleep(seconds)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 *Reminder!*\n\n{message}",
        parse_mode="Markdown"
    )


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /remind <time> <message>
    time format: 10s / 5m / 2h / 1d
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⏰ *How to use /remind:*\n\n"
            "`/remind 10m Call mom`\n"
            "`/remind 2h Submit assignment`\n"
            "`/remind 1d Exam tomorrow`\n\n"
            "⏱ Formats: `s` seconds · `m` minutes · `h` hours · `d` days",
            parse_mode="Markdown"
        )
        return

    time_str  = context.args[0]
    reminder_msg = " ".join(context.args[1:])
    seconds   = parse_time(time_str)

    if seconds is None:
        await update.message.reply_text(
            "❌ Invalid time format!\n"
            "Use: `10s`, `5m`, `2h`, `1d`",
            parse_mode="Markdown"
        )
        return

    if seconds > 7 * 86400:
        await update.message.reply_text("❌ Max reminder time is 7 days.")
        return

    chat_id = update.effective_chat.id
    fire_at = datetime.now() + timedelta(seconds=seconds)

    # Schedule the reminder as a background task
    asyncio.create_task(
        remind_after(seconds, chat_id, reminder_msg, context)
    )

    # Human-readable time display
    if seconds < 60:
        readable = f"{seconds} seconds"
    elif seconds < 3600:
        readable = f"{seconds // 60} minutes"
    elif seconds < 86400:
        readable = f"{seconds // 3600} hours"
    else:
        readable = f"{seconds // 86400} days"

    await update.message.reply_text(
        f"✅ *Reminder set!*\n\n"
        f"📝 {reminder_msg}\n"
        f"⏰ I'll remind you in *{readable}*\n"
        f"🕐 At: {fire_at.strftime('%I:%M %p')}",
        parse_mode="Markdown"
    )
