# ============================================================
#  handlers/admin.py
#  Admin-only commands — only Vikram can use these!
#
#  HOW TO GET YOUR TELEGRAM USER ID:
#    Open Telegram → search @userinfobot → send /start
#    It will show your numeric User ID
#    Paste it in ADMIN_ID below
# ============================================================

import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

# ── Your Telegram user ID ─────────────────────────────────
# Replace with your actual ID from @userinfobot
ADMIN_ID = int(os.environ.get("ADMIN_ID", "000000000"))

# File to track all users who have used the bot
USERS_FILE = "users_db.json"


def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(data: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def register_user(user_id: int, username: str, first_name: str):
    """Called every time a user interacts — tracks all users."""
    users = load_users()
    uid   = str(user_id)
    if uid not in users:
        users[uid] = {
            "username":   username or "unknown",
            "first_name": first_name or "unknown",
            "joined":     datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "messages":   0
        }
    users[uid]["messages"] = users[uid].get("messages", 0) + 1
    save_users(users)


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ── Admin: /broadcast ─────────────────────────────────────
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /broadcast <message>
    Sends a message to ALL users who have used the bot.
    Admin only.
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if not context.args:
        await update.message.reply_text(
            "📢 *Broadcast Usage:*\n`/broadcast Your message here`",
            parse_mode="Markdown"
        )
        return

    message = " ".join(context.args)
    users   = load_users()

    if not users:
        await update.message.reply_text("No users found in database yet.")
        return

    sent = 0
    failed = 0
    status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")

    for uid in users:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *Message from Vikram:*\n\n{message}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            failed += 1  # User may have blocked the bot

    await status_msg.edit_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"📤 Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total users: {len(users)}",
        parse_mode="Markdown"
    )


# ── Admin: /stats ─────────────────────────────────────────
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stats — Show bot usage statistics.
    Admin gets full stats, users get personal stats.
    """
    user_id = update.effective_user.id
    users   = load_users()
    uid     = str(user_id)

    if is_admin(user_id):
        # Admin sees ALL stats
        total_users    = len(users)
        total_messages = sum(u.get("messages", 0) for u in users.values())
        top_users      = sorted(users.items(), key=lambda x: x[1].get("messages", 0), reverse=True)[:5]

        lines = [
            "⚙️ *Bot Admin Stats*\n",
            f"👥 Total Users: *{total_users}*",
            f"💬 Total Messages: *{total_messages}*\n",
            "🏆 *Top Users:*"
        ]
        for i, (uid2, data) in enumerate(top_users, 1):
            name = data.get("first_name", "Unknown")
            msgs = data.get("messages", 0)
            lines.append(f"{i}. {name} — {msgs} messages")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    else:
        # Regular user sees only their own stats
        if uid not in users:
            await update.message.reply_text("No stats found for you yet. Send a few messages first!")
            return

        u = users[uid]
        await update.message.reply_text(
            f"📊 *Your Stats*\n\n"
            f"👤 Name: {u.get('first_name', 'Unknown')}\n"
            f"💬 Messages sent: *{u.get('messages', 0)}*\n"
            f"📅 First used: {u.get('joined', 'Unknown')}",
            parse_mode="Markdown"
        )


# ── Admin: /users ─────────────────────────────────────────
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /users — List all registered users. Admin only.
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command.")
        return

    users = load_users()
    if not users:
        await update.message.reply_text("No users yet.")
        return

    lines = [f"👥 *All Bot Users ({len(users)})*\n"]
    for i, (uid, data) in enumerate(users.items(), 1):
        name  = data.get("first_name", "Unknown")
        uname = data.get("username", "no username")
        msgs  = data.get("messages", 0)
        lines.append(f"{i}. *{name}* (@{uname}) — {msgs} msgs")

    text = "\n".join(lines)
    # Split if too long
    if len(text) > 4000:
        text = text[:4000] + "\n\n_(truncated)_"

    await update.message.reply_text(text, parse_mode="Markdown")
