# ============================================================
#  handlers/group_admin.py
#  Group management features (works in groups & supergroups)
#
#  /welcome setup <message> — Auto-welcome new members
#  /warn @user [reason]     — Warn a user (3 = kick)
#  /mute @user <time>       — Temporarily mute
#  /antiflood on/off        — Auto-delete flood messages
#  /report                  — Report a message to admins
#  /rules [set <rules>]     — Set/show group rules
#  /tagall                  — Tag all members (admin only)
# ============================================================

import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

GROUP_DATA_FILE = "group_data.json"

# In-memory flood tracking: { chat_id: { user_id: [timestamps] } }
flood_tracker: dict[str, dict] = {}
FLOOD_LIMIT   = 5    # messages
FLOOD_WINDOW  = 3    # seconds


def load_group_data() -> dict:
    if os.path.exists(GROUP_DATA_FILE):
        with open(GROUP_DATA_FILE) as f:
            return json.load(f)
    return {}


def save_group_data(data: dict):
    with open(GROUP_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_group(chat_id: str) -> dict:
    data = load_group_data()
    if chat_id not in data:
        data[chat_id] = {"welcome": None, "rules": None, "warns": {}, "antiflood": False}
        save_group_data(data)
    return data[chat_id]


def save_group(chat_id: str, group: dict):
    data = load_group_data()
    data[chat_id] = group
    save_group_data(data)


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the command sender is a group admin."""
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def _parse_duration(text: str) -> int:
    """Parse '10m', '2h', '1d' → seconds. Default 10 minutes."""
    text = text.lower().strip()
    try:
        if text.endswith("d"):
            return int(text[:-1]) * 86400
        elif text.endswith("h"):
            return int(text[:-1]) * 3600
        elif text.endswith("m"):
            return int(text[:-1]) * 60
        else:
            return int(text) * 60  # assume minutes
    except Exception:
        return 600  # 10 minutes default


# ── /welcome ─────────────────────────────────────────────

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-trigger when new member joins. Registered as MessageHandler."""
    if not update.message or not update.message.new_chat_members:
        return

    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)
    welcome = group.get("welcome")

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or "Friend"

        if welcome:
            msg = welcome.replace("{name}", f"*{name}*").replace("{group}", update.effective_chat.title or "our group")
        else:
            msg = (
                f"👋 Welcome to the group, *{name}*! 🎉\n\n"
                f"Please read the /rules before chatting.\n"
                f"Have a great time here! 😊"
            )

        await update.message.reply_text(msg, parse_mode="Markdown")


async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/welcome setup <message> — Set custom welcome message. Use {name} and {group}."""
    if not await _is_admin(update, context):
        await update.message.reply_text("⛔ Admins only!")
        return

    if not context.args or context.args[0].lower() != "setup":
        chat_id = str(update.effective_chat.id)
        group   = get_group(chat_id)
        current = group.get("welcome", "Not set (using default)")
        await update.message.reply_text(
            f"👋 *Welcome Message Setup*\n\n"
            f"Current: _{current}_\n\n"
            f"Set with: `/welcome setup Hello {{name}}, welcome to {{group}}! 🎉`\n\n"
            f"Use `{{name}}` for member name, `{{group}}` for group name.\n"
            f"`/welcome off` to disable",
            parse_mode="Markdown"
        )
        return

    if len(context.args) >= 2 and context.args[1].lower() == "off":
        chat_id = str(update.effective_chat.id)
        group   = get_group(chat_id)
        group["welcome"] = None
        save_group(chat_id, group)
        await update.message.reply_text("✅ Welcome message disabled.")
        return

    message = " ".join(context.args[1:])
    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)
    group["welcome"] = message
    save_group(chat_id, group)
    await update.message.reply_text(
        f"✅ Welcome message set!\n\nPreview:\n_{message.replace('{name}', 'Vikram').replace('{group}', update.effective_chat.title or 'this group')}_",
        parse_mode="Markdown"
    )


# ── /warn ─────────────────────────────────────────────────

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/warn @user [reason] — Warn a user. 3 warnings = kick."""
    if not await _is_admin(update, context):
        await update.message.reply_text("⛔ Admins only!")
        return

    # Must be a reply OR have a mention
    target = None
    reason = "No reason given"

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        reason = " ".join(context.args) if context.args else reason
    elif context.args and update.message.entities:
        for ent in update.message.entities:
            if ent.type == "mention":
                mention = update.message.text[ent.offset:ent.offset + ent.length]
                try:
                    chat_member = await context.bot.get_chat_member(
                        update.effective_chat.id,
                        mention.lstrip("@")
                    )
                    target = chat_member.user
                    reason = " ".join(context.args[1:]) or reason
                except Exception:
                    pass
                break

    if not target:
        await update.message.reply_text(
            "❌ Reply to a message to warn that user, or tag them:\n"
            "`/warn @username reason`",
            parse_mode="Markdown"
        )
        return

    if target.is_bot:
        await update.message.reply_text("❌ Can't warn bots!")
        return

    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)
    uid     = str(target.id)

    if uid not in group["warns"]:
        group["warns"][uid] = []
    group["warns"][uid].append({
        "reason": reason,
        "by": update.effective_user.first_name,
        "time": datetime.now().strftime("%d %b %Y")
    })
    warn_count = len(group["warns"][uid])
    save_group(chat_id, group)

    if warn_count >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)  # kick not ban
            group["warns"][uid] = []
            save_group(chat_id, group)
            await update.message.reply_text(
                f"🚫 *{target.first_name}* has been kicked after *3 warnings*!",
                parse_mode="Markdown"
            )
        except Exception:
            await update.message.reply_text(
                f"⚠️ *{target.first_name}* reached 3 warnings but I couldn't kick them.\n"
                "Make sure I'm an admin with ban permissions!",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            f"⚠️ *{target.first_name}* has been warned!\n\n"
            f"📋 Reason: {reason}\n"
            f"🔢 Warnings: *{warn_count}/3*\n\n"
            f"_{3 - warn_count} more warning(s) = kick_",
            parse_mode="Markdown"
        )


async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/warnings — Check your own warnings or reply to check someone else's."""
    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        target = update.effective_user

    uid    = str(target.id)
    warns  = group["warns"].get(uid, [])
    count  = len(warns)

    if count == 0:
        await update.message.reply_text(f"✅ *{target.first_name}* has no warnings. Clean record! 😇", parse_mode="Markdown")
    else:
        lines = [f"⚠️ *{target.first_name}* — {count}/3 warnings\n"]
        for i, w in enumerate(warns, 1):
            lines.append(f"{i}. _{w['reason']}_ (by {w['by']}, {w['time']})")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def resetwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resetwarn — Reset warnings for replied user. Admin only."""
    if not await _is_admin(update, context):
        await update.message.reply_text("⛔ Admins only!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to reset their warnings.")
        return

    target  = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)
    group["warns"][str(target.id)] = []
    save_group(chat_id, group)
    await update.message.reply_text(f"✅ Warnings reset for *{target.first_name}*.", parse_mode="Markdown")


# ── /mute ─────────────────────────────────────────────────

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mute @user <duration> — Mute a user. Duration: 10m, 2h, 1d."""
    if not await _is_admin(update, context):
        await update.message.reply_text("⛔ Admins only!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Reply to a user's message to mute them.\n"
            "Example: reply + `/mute 30m`",
            parse_mode="Markdown"
        )
        return

    target   = update.message.reply_to_message.from_user
    duration = context.args[0] if context.args else "10m"
    seconds  = _parse_duration(duration)
    until    = datetime.now() + timedelta(seconds=seconds)

    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
            ),
            until_date=until,
        )
        await update.message.reply_text(
            f"🔇 *{target.first_name}* has been muted for *{duration}*!\n"
            f"_Until: {until.strftime('%d %b %Y %I:%M %p')}_",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Failed to mute. Make sure I'm an admin with restrict permissions!")


async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unmute — Unmute a replied user."""
    if not await _is_admin(update, context):
        await update.message.reply_text("⛔ Admins only!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a muted user's message.")
        return

    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text(f"🔊 *{target.first_name}* has been unmuted!", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Failed to unmute.")


# ── /antiflood ────────────────────────────────────────────

async def antiflood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/antiflood on/off — Toggle flood protection."""
    if not await _is_admin(update, context):
        await update.message.reply_text("⛔ Admins only!")
        return

    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)

    if not context.args:
        status = "✅ ON" if group.get("antiflood") else "❌ OFF"
        await update.message.reply_text(
            f"🌊 *Antiflood* is currently: {status}\n\n"
            f"Toggle: `/antiflood on` or `/antiflood off`\n"
            f"_Kicks users who send {FLOOD_LIMIT}+ messages in {FLOOD_WINDOW} seconds._",
            parse_mode="Markdown"
        )
        return

    setting = context.args[0].lower()
    if setting == "on":
        group["antiflood"] = True
        save_group(chat_id, group)
        await update.message.reply_text(f"✅ Antiflood enabled! Users sending {FLOOD_LIMIT}+ messages in {FLOOD_WINDOW}s will be muted.")
    elif setting == "off":
        group["antiflood"] = False
        save_group(chat_id, group)
        await update.message.reply_text("❌ Antiflood disabled.")
    else:
        await update.message.reply_text("Usage: `/antiflood on` or `/antiflood off`", parse_mode="Markdown")


async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message handler — checks for flooding. Register as group=0 handler."""
    if not update.message or not update.effective_chat or not update.effective_user:
        return

    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)

    if not group.get("antiflood"):
        return

    user_id = str(update.effective_user.id)
    now     = datetime.now().timestamp()

    if chat_id not in flood_tracker:
        flood_tracker[chat_id] = {}
    if user_id not in flood_tracker[chat_id]:
        flood_tracker[chat_id][user_id] = []

    # Keep only recent timestamps
    flood_tracker[chat_id][user_id] = [
        t for t in flood_tracker[chat_id][user_id] if now - t < FLOOD_WINDOW
    ]
    flood_tracker[chat_id][user_id].append(now)

    if len(flood_tracker[chat_id][user_id]) >= FLOOD_LIMIT:
        flood_tracker[chat_id][user_id] = []
        try:
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=update.effective_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(minutes=5),
            )
            await update.message.reply_text(
                f"🌊 *{update.effective_user.first_name}* was muted for 5 minutes due to flooding!",
                parse_mode="Markdown"
            )
        except Exception:
            pass


# ── /report ───────────────────────────────────────────────

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/report — Report a replied message to group admins."""
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Reply to the message you want to report, then type /report"
        )
        return

    reported_msg  = update.message.reply_to_message
    reported_user = reported_msg.from_user
    reporter      = update.effective_user

    # Get admin list
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_mentions = " ".join(
            f"@{a.user.username}" for a in admins
            if a.user.username and not a.user.is_bot
        )
    except Exception:
        admin_mentions = "Admins"

    reason = " ".join(context.args) if context.args else "No reason specified"

    await update.message.reply_text(
        f"🚨 *Report Submitted!*\n\n"
        f"👤 Reported: *{reported_user.first_name}*\n"
        f"📝 Message: _{reported_msg.text or '[media]'}_\n"
        f"⚠️ Reason: {reason}\n\n"
        f"Notifying admins: {admin_mentions}",
        parse_mode="Markdown"
    )


# ── /rules ────────────────────────────────────────────────

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/rules — Show rules. /rules set <rules> to set them (admin)."""
    chat_id = str(update.effective_chat.id)
    group   = get_group(chat_id)

    if context.args and context.args[0].lower() == "set":
        if not await _is_admin(update, context):
            await update.message.reply_text("⛔ Only admins can set rules!")
            return
        rules_text = " ".join(context.args[1:])
        if not rules_text:
            await update.message.reply_text("❌ Usage: `/rules set 1. Be respectful 2. No spam`", parse_mode="Markdown")
            return
        group["rules"] = rules_text
        save_group(chat_id, group)
        await update.message.reply_text("✅ Group rules updated!")
        return

    rules = group.get("rules")
    if not rules:
        await update.message.reply_text(
            "📋 No rules set yet.\n\n"
            "Admins: `/rules set 1. Be kind 2. No spam`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"📋 *{update.effective_chat.title} — Rules*\n\n{rules}\n\n"
        f"_Please follow these rules to keep the group friendly!_ 🙏",
        parse_mode="Markdown"
    )


# ── /tagall ───────────────────────────────────────────────

async def tagall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tagall <message> — Tag all members. Admin only."""
    if not await _is_admin(update, context):
        await update.message.reply_text("⛔ Admins only!")
        return

    announcement = " ".join(context.args) if context.args else "📢 Attention everyone!"

    try:
        members_text = f"📢 *{announcement}*\n\n"
        try:
            admins = await context.bot.get_chat_administrators(update.effective_chat.id)
            tags   = " ".join(f"@{a.user.username}" for a in admins if a.user.username and not a.user.is_bot)
            members_text += f"Admins: {tags}\n\n"
        except Exception:
            pass
        members_text += "_Note: Telegram limits tagging to admins only via bot API. Ask members to check pinned messages for full announcements._"

        await update.message.reply_text(members_text, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Failed to tag members.")
