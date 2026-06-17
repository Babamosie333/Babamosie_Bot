# ============================================================
#  handlers/tools.py
#  /password — Secure password generator
#  /qr <text> — QR code generator
#  /poll <question>, <opt1>, <opt2>, ... — Poll creator
# ============================================================

import random
import string
import io
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ── stores poll votes: { poll_id: {option: [user_ids] } } ──
poll_data: dict[str, dict] = {}
poll_counter = 0


# ════════════════════════════════════════════════
#  PASSWORD GENERATOR
# ════════════════════════════════════════════════

async def password_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /password [length] [type]
    Types: strong (default), pin, memorable
    Examples:
      /password
      /password 20
      /password 6 pin
      /password 16 strong
    """
    length = 16
    pwd_type = "strong"

    if context.args:
        for arg in context.args:
            if arg.isdigit():
                length = min(max(int(arg), 4), 64)   # clamp between 4-64
            elif arg.lower() in ("strong", "pin", "memorable"):
                pwd_type = arg.lower()

    if pwd_type == "pin":
        password = "".join(random.choices(string.digits, k=length))
        label    = f"🔢 PIN ({length} digits)"

    elif pwd_type == "memorable":
        # Word-based password easy to remember
        words  = ["Tiger","Sky","River","Moon","Star","Rock","Fire","Storm",
                  "Eagle","Wolf","Blade","Nova","Pixel","Cyber","Dark","Neon"]
        parts  = [random.choice(words) for _ in range(3)]
        number = random.randint(10, 99)
        symbol = random.choice("!@#$%^&*")
        password = f"{parts[0]}{symbol}{parts[1]}{number}{parts[2]}"
        label    = "🧠 Memorable password"

    else:
        # Strong: letters + digits + symbols
        chars    = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        password = "".join(random.choices(chars, k=length))
        # Ensure at least one of each type
        password = (
            random.choice(string.ascii_uppercase) +
            random.choice(string.ascii_lowercase) +
            random.choice(string.digits) +
            random.choice("!@#$%^&*") +
            password[4:]
        )
        password = "".join(random.sample(password, len(password)))  # shuffle
        label    = f"🔐 Strong password ({length} chars)"

    # Strength indicator
    if len(password) >= 16 and pwd_type == "strong":
        strength = "💪 Very Strong"
    elif len(password) >= 12:
        strength = "✅ Strong"
    else:
        strength = "⚠️ Moderate"

    await update.message.reply_text(
        f"🔐 *Password Generator*\n\n"
        f"*{label}*\n"
        f"Strength: {strength}\n\n"
        f"`{password}`\n\n"
        f"_(Tap the password above to copy it!)_\n\n"
        f"Other types:\n"
        f"`/password 6 pin` → PIN\n"
        f"`/password 20 strong` → Strong\n"
        f"`/password memorable` → Easy to remember",
        parse_mode="Markdown"
    )


# ════════════════════════════════════════════════
#  QR CODE GENERATOR
# ════════════════════════════════════════════════

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /qr <text or URL>
    Generates a QR code image for any text, URL, phone number, etc.
    """
    if not context.args:
        await update.message.reply_text(
            "📷 *How to use /qr:*\n\n"
            "`/qr https://vikramsingh.itsfolio.tech`\n"
            "`/qr Hello World`\n"
            "`/qr +91 9876543210`\n"
            "`/qr Pay me on UPI: vikram@upi`",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    await update.message.chat.send_action("upload_photo")

    try:
        # qr-server.com — completely free, no key, returns PNG image
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={requests.utils.quote(text)}"
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            await update.message.reply_text("❌ QR generation failed. Try again.")
            return

        # Send the image directly from bytes
        img_bytes = io.BytesIO(resp.content)
        img_bytes.name = "qrcode.png"

        await update.message.reply_photo(
            photo=img_bytes,
            caption=f"📷 *QR Code*\n\n`{text[:100]}`",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text("❌ QR service unavailable. Try again later.")


# ════════════════════════════════════════════════
#  POLL CREATOR
# ════════════════════════════════════════════════

async def poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /poll <Question>, <Option1>, <Option2>, [Option3], ...
    Example: /poll Favorite language?, Python, JavaScript, Java
    """
    global poll_counter

    if not context.args:
        await update.message.reply_text(
            "🗳 *How to use /poll:*\n\n"
            "`/poll Favorite language?, Python, JavaScript, Java`\n"
            "`/poll Best food?, Pizza, Biryani, Burger, Pasta`\n\n"
            "Separate question and options with commas!",
            parse_mode="Markdown"
        )
        return

    full = " ".join(context.args)
    parts = [p.strip() for p in full.split(",")]

    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Need at least a question and 2 options!\n"
            "Example: `/poll Best language?, Python, JavaScript`",
            parse_mode="Markdown"
        )
        return

    if len(parts) > 11:   # 1 question + 10 options max
        await update.message.reply_text("❌ Max 10 options allowed.")
        return

    question = parts[0]
    options  = parts[1:]

    poll_counter += 1
    poll_id = f"poll_{poll_counter}"

    # Initialize vote tracking
    poll_data[poll_id] = {opt: [] for opt in options}

    # Build keyboard — one button per option
    keyboard = []
    for i, opt in enumerate(options):
        emoji = ["🅐","🅑","🅒","🅓","🅔","🅕","🅖","🅗","🅘","🅙"][i]
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {opt}",
                callback_data=f"poll|{poll_id}|{opt[:30]}"
            )
        ])
    # Add results button
    keyboard.append([
        InlineKeyboardButton("📊 Show Results", callback_data=f"pollresult|{poll_id}")
    ])

    await update.message.reply_text(
        f"🗳 *{question}*\n\n"
        f"_Tap an option to vote!_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def poll_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll vote button taps and result requests."""
    query   = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()

    # ── Show results ───────────────────────────────────────
    if query.data.startswith("pollresult|"):
        poll_id = query.data.split("|")[1]
        if poll_id not in poll_data:
            await query.answer("Poll not found!", show_alert=True)
            return

        votes   = poll_data[poll_id]
        total   = sum(len(v) for v in votes.values())
        lines   = ["📊 *Poll Results*\n"]

        for opt, voters in votes.items():
            count = len(voters)
            pct   = int((count / total * 100) if total > 0 else 0)
            bar   = "█" * (pct // 10) + "░" * (10 - pct // 10)
            lines.append(f"*{opt}*\n{bar} {pct}% ({count} votes)")

        lines.append(f"\n👥 Total votes: {total}")
        await query.message.reply_text("\n\n".join(lines), parse_mode="Markdown")
        return

    # ── Record vote ────────────────────────────────────────
    if query.data.startswith("poll|"):
        parts   = query.data.split("|")
        poll_id = parts[1]
        option  = parts[2]

        if poll_id not in poll_data:
            await query.answer("This poll has expired!", show_alert=True)
            return

        # Check if user already voted
        already_voted = any(user_id in voters for voters in poll_data[poll_id].values())
        if already_voted:
            await query.answer("⚠️ You already voted in this poll!", show_alert=True)
            return

        # Find matching option (partial match since we truncated to 30 chars)
        matched = None
        for opt in poll_data[poll_id]:
            if opt[:30] == option:
                matched = opt
                break

        if not matched:
            await query.answer("Option not found!", show_alert=True)
            return

        poll_data[poll_id][matched].append(user_id)
        total = sum(len(v) for v in poll_data[poll_id].values())
        await query.answer(f"✅ Voted for '{matched}'! Total votes: {total}", show_alert=True)
