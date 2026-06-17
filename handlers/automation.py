# ============================================================
#  handlers/automation.py
#  /subscribe news <keyword>    — Daily news alerts
#  /unsubscribe                 — Remove subscription
#  /pricealert BTC 50000        — Crypto price alert
#  /birthday add <name> <DD-MM> — Birthday reminder
#  /habit add/done/streak <name>— Daily habit tracker
#  /journal [entry]             — Private daily journal
# ============================================================

import json
import os
import requests
import asyncio
from datetime import datetime, date
from telegram import Update
from telegram.ext import ContextTypes, Application

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

SUBS_FILE      = "subscriptions.json"
ALERTS_FILE    = "price_alerts.json"
BIRTHDAYS_FILE = "birthdays.json"
HABITS_FILE    = "habits.json"
JOURNAL_FILE   = "journals.json"


def _jload(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _jsave(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── /subscribe ────────────────────────────────────────────

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /subscribe news <keyword>  — Get daily news on a keyword
    /subscribe list            — List your subscriptions
    """
    user_id = str(update.effective_user.id)
    subs    = _jload(SUBS_FILE)

    if not context.args:
        user_subs = subs.get(user_id, [])
        sub_list  = "\n".join(f"• {s}" for s in user_subs) if user_subs else "None"
        await update.message.reply_text(
            f"📰 *News Subscriptions*\n\n"
            f"Your subscriptions:\n{sub_list}\n\n"
            f"`/subscribe news AI` — Daily AI news\n"
            f"`/subscribe news cricket` — Cricket updates\n"
            f"`/subscribe news India` — India headlines\n"
            f"`/unsubscribe <keyword>` — Remove a subscription\n\n"
            f"_News is delivered daily at 8 AM. Use /testbrief to test._",
            parse_mode="Markdown"
        )
        return

    if context.args[0].lower() == "list":
        user_subs = subs.get(user_id, [])
        sub_list  = "\n".join(f"• {s}" for s in user_subs) if user_subs else "None yet"
        await update.message.reply_text(f"📰 Your subscriptions:\n{sub_list}\n\nAdd: `/subscribe news <keyword>`", parse_mode="Markdown")
        return

    if context.args[0].lower() != "news" or len(context.args) < 2:
        await update.message.reply_text("Usage: `/subscribe news <keyword>`\nExample: `/subscribe news Bitcoin`", parse_mode="Markdown")
        return

    keyword = " ".join(context.args[1:]).lower()
    if user_id not in subs:
        subs[user_id] = []

    # Save chat_id too for sending
    chat_id = str(update.effective_chat.id)
    entry   = f"{keyword}|{chat_id}"

    if keyword in [s.split("|")[0] for s in subs[user_id]]:
        await update.message.reply_text(f"ℹ️ You're already subscribed to *{keyword}* news!", parse_mode="Markdown")
        return

    subs[user_id].append(entry)
    _jsave(SUBS_FILE, subs)

    await update.message.reply_text(
        f"✅ Subscribed to *{keyword}* news!\n\n"
        f"📰 You'll get daily updates every morning.\n"
        f"Use `/unsubscribe {keyword}` to cancel.",
        parse_mode="Markdown"
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unsubscribe <keyword> — Remove a news subscription."""
    user_id = str(update.effective_user.id)
    subs    = _jload(SUBS_FILE)

    if not context.args:
        await update.message.reply_text("Usage: `/unsubscribe <keyword>`", parse_mode="Markdown")
        return

    keyword    = " ".join(context.args).lower()
    user_subs  = subs.get(user_id, [])
    new_subs   = [s for s in user_subs if s.split("|")[0] != keyword]

    if len(new_subs) == len(user_subs):
        await update.message.reply_text(f"❌ You're not subscribed to *{keyword}*.", parse_mode="Markdown")
        return

    subs[user_id] = new_subs
    _jsave(SUBS_FILE, subs)
    await update.message.reply_text(f"✅ Unsubscribed from *{keyword}* news.", parse_mode="Markdown")


# ── /pricealert ───────────────────────────────────────────

COIN_MAP = {
    "btc": "bitcoin", "eth": "ethereum", "doge": "dogecoin",
    "bnb": "binancecoin", "sol": "solana", "ada": "cardano",
    "xrp": "ripple", "matic": "matic-network",
}


async def pricealert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pricealert <coin> <target_price_USD> — Alert when crypto hits target."""
    user_id = str(update.effective_user.id)
    alerts  = _jload(ALERTS_FILE)

    if not context.args or context.args[0].lower() == "list":
        user_alerts = alerts.get(user_id, [])
        if not user_alerts:
            await update.message.reply_text(
                "🔔 *Price Alert Setup*\n\n"
                "`/pricealert BTC 70000` — Alert when BTC hits $70,000\n"
                "`/pricealert ETH 5000` — Alert when ETH hits $5,000\n"
                "`/pricealert DOGE 0.5` — Alert when DOGE hits $0.50\n\n"
                "_Checked every 30 minutes while bot is running._",
                parse_mode="Markdown"
            )
            return
        lines = ["🔔 *Your Price Alerts*\n"]
        for a in user_alerts:
            lines.append(f"• {a['coin'].upper()} → ${a['target']:,.2f} ({a['direction']})")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/pricealert BTC 70000`", parse_mode="Markdown")
        return

    coin_input = context.args[0].lower()
    coin_id    = COIN_MAP.get(coin_input, coin_input)

    try:
        target = float(context.args[1].replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Example: `/pricealert BTC 70000`", parse_mode="Markdown")
        return

    # Get current price to determine direction
    try:
        resp    = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd",
            timeout=8
        )
        current = resp.json()[coin_id]["usd"]
        direction = "above" if target > current else "below"
    except Exception:
        current   = 0
        direction = "above"

    if user_id not in alerts:
        alerts[user_id] = []

    alerts[user_id].append({
        "coin": coin_input, "coin_id": coin_id, "target": target,
        "direction": direction, "chat_id": str(update.effective_chat.id),
        "triggered": False
    })
    _jsave(ALERTS_FILE, alerts)

    await update.message.reply_text(
        f"🔔 *Price Alert Set!*\n\n"
        f"💰 {coin_input.upper()} → *${target:,.2f}*\n"
        f"📊 Current: ${current:,.2f}\n"
        f"📈 Alert when: price goes *{direction}* ${target:,.2f}\n\n"
        f"_I'll check every 30 minutes and notify you!_",
        parse_mode="Markdown"
    )


async def check_price_alerts(app: Application):
    """Background task — check price alerts every 30 minutes."""
    alerts = _jload(ALERTS_FILE)
    changed = False

    for user_id, user_alerts in alerts.items():
        for alert in user_alerts:
            if alert.get("triggered"):
                continue
            try:
                resp    = requests.get(
                    f"https://api.coingecko.com/api/v3/simple/price?ids={alert['coin_id']}&vs_currencies=usd",
                    timeout=8
                )
                current = resp.json()[alert["coin_id"]]["usd"]
                hit     = (alert["direction"] == "above" and current >= alert["target"]) or \
                          (alert["direction"] == "below" and current <= alert["target"])

                if hit:
                    alert["triggered"] = True
                    changed = True
                    await app.bot.send_message(
                        chat_id=int(alert["chat_id"]),
                        text=(
                            f"🚨 *Price Alert Triggered!*\n\n"
                            f"💰 {alert['coin'].upper()} has gone {alert['direction']} "
                            f"your target of *${alert['target']:,.2f}*!\n\n"
                            f"📊 Current price: *${current:,.2f}*\n\n"
                            f"_Set a new alert: /pricealert_"
                        ),
                        parse_mode="Markdown"
                    )
            except Exception:
                pass

    if changed:
        _jsave(ALERTS_FILE, alerts)


# ── /birthday ─────────────────────────────────────────────

async def birthday_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /birthday add <Name> <DD-MM>   — Track a birthday
    /birthday list                 — List all birthdays
    /birthday del <Name>           — Delete a birthday
    """
    user_id = str(update.effective_user.id)
    bdays   = _jload(BIRTHDAYS_FILE)

    if not context.args:
        user_bdays = bdays.get(user_id, [])
        today      = date.today()
        upcoming   = []
        for b in user_bdays:
            try:
                bdate = datetime.strptime(b["date"], "%d-%m").replace(year=today.year).date()
                if bdate < today:
                    bdate = bdate.replace(year=today.year + 1)
                days_left = (bdate - today).days
                upcoming.append((days_left, b["name"], b["date"]))
            except Exception:
                pass

        upcoming.sort()
        lines = ["🎂 *Birthday Tracker*\n"]
        for days, name, bdate in upcoming[:5]:
            emoji = "🎉" if days == 0 else "🎂"
            note  = "**TODAY!**" if days == 0 else f"in {days} days"
            lines.append(f"{emoji} *{name}* ({bdate}) — {note}")

        if not upcoming:
            lines.append("No birthdays saved yet!")

        lines.append(
            "\n`/birthday add Maa 15-10` — Add birthday\n"
            "`/birthday list` — See all\n"
            "`/birthday del Maa` — Remove"
        )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    sub = context.args[0].lower()

    if sub == "add":
        if len(context.args) < 3:
            await update.message.reply_text("Usage: `/birthday add <Name> <DD-MM>`\nExample: `/birthday add Rahul 25-12`", parse_mode="Markdown")
            return
        name  = context.args[1]
        bdate = context.args[2]
        try:
            datetime.strptime(bdate, "%d-%m")
        except ValueError:
            await update.message.reply_text("❌ Invalid date format. Use DD-MM\nExample: `25-12` for December 25", parse_mode="Markdown")
            return

        if user_id not in bdays:
            bdays[user_id] = []
        bdays[user_id].append({"name": name, "date": bdate, "chat_id": str(update.effective_chat.id)})
        _jsave(BIRTHDAYS_FILE, bdays)
        await update.message.reply_text(f"🎂 Birthday added!\n*{name}* — {bdate} 🎉\n\n_I'll remind you on their birthday!_", parse_mode="Markdown")

    elif sub == "list":
        user_bdays = bdays.get(user_id, [])
        if not user_bdays:
            await update.message.reply_text("📭 No birthdays saved! Add: `/birthday add Name DD-MM`", parse_mode="Markdown")
            return
        today = date.today()
        lines = [f"🎂 *Birthdays ({len(user_bdays)})*\n"]
        for b in user_bdays:
            try:
                bdate = datetime.strptime(b["date"], "%d-%m").replace(year=today.year).date()
                if bdate < today:
                    bdate = bdate.replace(year=today.year + 1)
                days_left = (bdate - today).days
                lines.append(f"• *{b['name']}* ({b['date']}) — {days_left} days away")
            except Exception:
                lines.append(f"• *{b['name']}* ({b['date']})")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif sub == "del":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/birthday del <Name>`", parse_mode="Markdown")
            return
        name       = context.args[1]
        user_bdays = bdays.get(user_id, [])
        new_bdays  = [b for b in user_bdays if b["name"].lower() != name.lower()]
        if len(new_bdays) == len(user_bdays):
            await update.message.reply_text(f"❌ No birthday found for *{name}*.", parse_mode="Markdown")
            return
        bdays[user_id] = new_bdays
        _jsave(BIRTHDAYS_FILE, bdays)
        await update.message.reply_text(f"✅ Removed birthday for *{name}*.", parse_mode="Markdown")


async def check_birthdays(app: Application):
    """Called daily — sends birthday messages."""
    bdays = _jload(BIRTHDAYS_FILE)
    today = date.today().strftime("%d-%m")

    for user_id, user_bdays in bdays.items():
        for b in user_bdays:
            if b["date"] == today:
                try:
                    await app.bot.send_message(
                        chat_id=int(b["chat_id"]),
                        text=(
                            f"🎂 *Happy Birthday, {b['name']}!* 🎉\n\n"
                            f"🥳 Wishing them a wonderful day!\n"
                            f"Don't forget to wish them! 🎁"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass


# ── /habit ────────────────────────────────────────────────

async def habit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /habit add <name>    — Add a habit to track
    /habit done <name>   — Mark habit done for today
    /habit streak        — See all habits and streaks
    /habit list          — List your habits
    /habit del <name>    — Remove a habit
    """
    user_id = str(update.effective_user.id)
    habits  = _jload(HABITS_FILE)
    today   = date.today().isoformat()

    if not context.args:
        await update.message.reply_text(
            "🏃 *Habit Tracker*\n\n"
            "`/habit add Exercise` — Add a habit\n"
            "`/habit done Exercise` — Mark done today ✅\n"
            "`/habit streak` — See your streaks 🔥\n"
            "`/habit list` — See all habits\n"
            "`/habit del Exercise` — Remove a habit",
            parse_mode="Markdown"
        )
        return

    sub = context.args[0].lower()
    if user_id not in habits:
        habits[user_id] = {}

    if sub == "add":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/habit add <habit name>`", parse_mode="Markdown")
            return
        name = " ".join(context.args[1:])
        if name.lower() in [h.lower() for h in habits[user_id]]:
            await update.message.reply_text(f"ℹ️ Habit *{name}* already exists!", parse_mode="Markdown")
            return
        habits[user_id][name] = {"streak": 0, "last_done": None, "done_dates": []}
        _jsave(HABITS_FILE, habits)
        await update.message.reply_text(f"✅ Habit *{name}* added!\n\nMark it done daily: `/habit done {name}`", parse_mode="Markdown")

    elif sub == "done":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/habit done <habit name>`", parse_mode="Markdown")
            return
        name = " ".join(context.args[1:])
        # Find case-insensitive match
        match = next((h for h in habits[user_id] if h.lower() == name.lower()), None)
        if not match:
            await update.message.reply_text(f"❌ Habit *{name}* not found. Add it: `/habit add {name}`", parse_mode="Markdown")
            return

        h = habits[user_id][match]
        if h.get("last_done") == today:
            await update.message.reply_text(f"✅ You already completed *{match}* today! 🔥\nStreak: {h['streak']} days", parse_mode="Markdown")
            return

        # Update streak
        yesterday = (date.today().replace(day=date.today().day - 1)).isoformat() if date.today().day > 1 else None
        if h.get("last_done") == yesterday:
            h["streak"] += 1
        else:
            h["streak"] = 1

        h["last_done"] = today
        if today not in h.get("done_dates", []):
            h.setdefault("done_dates", []).append(today)
        _jsave(HABITS_FILE, habits)

        streak = h["streak"]
        fire   = "🔥" * min(streak, 5)
        await update.message.reply_text(
            f"✅ *{match}* done for today!\n\n"
            f"🔥 Streak: *{streak} day{'s' if streak != 1 else ''}* {fire}\n\n"
            f"_Keep it up! Consistency is key. 💪_",
            parse_mode="Markdown"
        )

    elif sub in ("streak", "list"):
        user_habits = habits.get(user_id, {})
        if not user_habits:
            await update.message.reply_text("📭 No habits yet! Start: `/habit add Exercise`", parse_mode="Markdown")
            return
        lines = [f"🏃 *Your Habits & Streaks*\n"]
        for name, h in user_habits.items():
            streak   = h.get("streak", 0)
            last     = h.get("last_done", "Never")
            done_today = last == today
            status   = "✅" if done_today else "⬜"
            fire     = "🔥" * min(streak, 5)
            lines.append(f"{status} *{name}* — {streak} day streak {fire}")
        lines.append(f"\n_Mark done: `/habit done <name>`_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif sub == "del":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/habit del <name>`", parse_mode="Markdown")
            return
        name  = " ".join(context.args[1:])
        match = next((h for h in habits[user_id] if h.lower() == name.lower()), None)
        if not match:
            await update.message.reply_text(f"❌ Habit *{name}* not found.", parse_mode="Markdown")
            return
        del habits[user_id][match]
        _jsave(HABITS_FILE, habits)
        await update.message.reply_text(f"🗑 Habit *{match}* removed.", parse_mode="Markdown")


# ── /journal ─────────────────────────────────────────────

async def journal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /journal <entry>    — Write today's journal entry
    /journal view       — View today's entry
    /journal history    — Last 7 entries
    """
    user_id = str(update.effective_user.id)
    journals = _jload(JOURNAL_FILE)
    today   = date.today().isoformat()

    if not context.args:
        today_entry = journals.get(user_id, {}).get(today, {}).get("entry")
        if today_entry:
            await update.message.reply_text(
                f"📔 *Today's Journal*\n_{today}_\n\n{today_entry}\n\n"
                f"_Update it: `/journal <new entry>`_\n"
                f"_History: `/journal history`_",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"📔 *Daily Journal*\n\n"
                f"Write today's entry:\n`/journal Had a productive day. Learned about APIs...`\n\n"
                f"View history: `/journal history`",
                parse_mode="Markdown"
            )
        return

    if context.args[0].lower() == "view":
        entry = journals.get(user_id, {}).get(today, {}).get("entry", "No entry for today yet.")
        await update.message.reply_text(
            f"📔 *Today's Journal — {today}*\n\n{entry}",
            parse_mode="Markdown"
        )
        return

    if context.args[0].lower() == "history":
        user_journal = journals.get(user_id, {})
        if not user_journal:
            await update.message.reply_text("📭 No journal entries yet. Start: `/journal Today was great!`", parse_mode="Markdown")
            return
        sorted_entries = sorted(user_journal.items(), reverse=True)[:7]
        lines = ["📔 *Journal — Last 7 Entries*\n"]
        for entry_date, data in sorted_entries:
            text  = data.get("entry", "")[:100]
            mood  = data.get("mood", "")
            lines.append(f"📅 *{entry_date}* {mood}\n_{text}..._\n")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # Write journal entry
    entry_text = " ".join(context.args)
    if user_id not in journals:
        journals[user_id] = {}

    # AI mood analysis
    mood_emoji = "📝"
    try:
        mood_resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "Analyze the mood of this journal entry and respond with ONLY ONE emoji that best represents the mood. Choose from: 😊 😔 😤 😰 🥳 😴 😐 🤔 ❤️ 💪"},
                    {"role": "user", "content": entry_text}
                ],
                "max_tokens": 5,
            },
            timeout=8
        )
        mood_emoji = mood_resp.json()["choices"][0]["message"]["content"].strip()[:2]
    except Exception:
        pass

    journals[user_id][today] = {"entry": entry_text, "mood": mood_emoji, "time": datetime.now().strftime("%I:%M %p")}
    _jsave(JOURNAL_FILE, journals)

    await update.message.reply_text(
        f"📔 *Journal Saved!* {mood_emoji}\n\n"
        f"_{entry_text[:200]}_\n\n"
        f"📅 {today}\n"
        f"View history: `/journal history`",
        parse_mode="Markdown"
    )
