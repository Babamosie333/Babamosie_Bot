# ============================================================
#  handlers/notes.py
#  /note, /notes, /clearnotes — per-user note saving
#
#  Notes are stored in a local JSON file (notes_db.json)
#  so they survive bot restarts!
# ============================================================

import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

# Path to the JSON file that stores all users' notes
NOTES_FILE = "notes_db.json"


def load_notes() -> dict:
    """Load notes from the JSON file. Returns empty dict if file doesn't exist."""
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r") as f:
            return json.load(f)
    return {}


def save_notes(data: dict):
    """Save the notes dictionary back to the JSON file."""
    with open(NOTES_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/note <text> — Save a note for this user."""
    if not context.args:
        await update.message.reply_text(
            "Please provide a note to save.\n"
            "Example: `/note Study for exam tomorrow`",
            parse_mode="Markdown"
        )
        return

    note_text = " ".join(context.args)                # Combine all words after /note
    user_id   = str(update.effective_user.id)         # Each user gets their own notes list
    timestamp = datetime.now().strftime("%d %b, %I:%M %p")

    # Load existing notes, add the new one, save back
    all_notes = load_notes()
    if user_id not in all_notes:
        all_notes[user_id] = []

    all_notes[user_id].append({
        "text": note_text,
        "time": timestamp
    })
    save_notes(all_notes)

    note_number = len(all_notes[user_id])
    await update.message.reply_text(
        f"✅ Note #{note_number} saved!\n`{note_text}`",
        parse_mode="Markdown"
    )


async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/notes — Show all saved notes for this user."""
    user_id   = str(update.effective_user.id)
    all_notes = load_notes()
    user_notes = all_notes.get(user_id, [])

    if not user_notes:
        await update.message.reply_text(
            "📝 You have no saved notes.\n"
            "Use `/note <text>` to save one!",
            parse_mode="Markdown"
        )
        return

    lines = [f"📝 *Your Notes ({len(user_notes)} total)*\n"]
    for i, note in enumerate(user_notes, 1):
        lines.append(f"*{i}.* {note['text']}\n   _🕐 {note['time']}_")

    lines.append("\nTo delete all: /clearnotes")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def clear_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/clearnotes — Delete all notes for this user."""
    user_id   = str(update.effective_user.id)
    all_notes = load_notes()

    if user_id not in all_notes or not all_notes[user_id]:
        await update.message.reply_text("You have no notes to clear.")
        return

    count = len(all_notes[user_id])
    all_notes[user_id] = []          # Empty the list
    save_notes(all_notes)

    await update.message.reply_text(f"🗑 Cleared all {count} notes successfully!")
