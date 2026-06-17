# ============================================================
#  handlers/lyrics.py
#  /lyrics <song name> [by artist]
#  Uses lyrics.ovh free API
#  Examples:
#    /lyrics Shape of You
#    /lyrics Tum Hi Ho by Arijit Singh
# ============================================================

import requests
from telegram import Update
from telegram.ext import ContextTypes


async def lyrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /lyrics <song> [by <artist>]
    Fetches song lyrics from lyrics.ovh (free, no key needed).
    """
    if not context.args:
        await update.message.reply_text(
            "🎵 *How to use /lyrics:*\n\n"
            "`/lyrics Shape of You`\n"
            "`/lyrics Tum Hi Ho by Arijit Singh`\n"
            "`/lyrics Believer by Imagine Dragons`\n\n"
            "💡 Tip: Adding 'by artist' gives better results!",
            parse_mode="Markdown"
        )
        return

    full_query = " ".join(context.args)
    await update.message.chat.send_action("typing")

    # Parse "song by artist" format
    if " by " in full_query.lower():
        idx    = full_query.lower().rfind(" by ")
        song   = full_query[:idx].strip()
        artist = full_query[idx + 4:].strip()
    else:
        song   = full_query.strip()
        artist = "unknown"

    try:
        # lyrics.ovh API — completely free, no key
        url  = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(song)}"
        resp = requests.get(url, timeout=10)

        if resp.status_code == 404 or "error" in resp.json():
            # Try searching without artist
            await update.message.reply_text(
                f"❌ Lyrics not found for *{song}*.\n\n"
                "Try adding the artist name:\n"
                f"`/lyrics {song} by Artist Name`",
                parse_mode="Markdown"
            )
            return

        data   = resp.json()
        lyrics = data.get("lyrics", "").strip()

        if not lyrics:
            await update.message.reply_text("❌ No lyrics found. Try a different song.")
            return

        # Telegram limit is 4096 chars — truncate if too long
        header = f"🎵 *{song.title()}*"
        if artist != "unknown":
            header += f"\n👤 _{artist.title()}_"
        header += "\n\n"

        # Send first chunk with header
        max_len   = 4000 - len(header)
        lines     = lyrics.split("\n")
        chunks    = []
        current   = ""

        for line in lines:
            if len(current) + len(line) + 1 > max_len:
                chunks.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            chunks.append(current)

        if not chunks:
            await update.message.reply_text("❌ Could not parse lyrics.")
            return

        # Send first chunk with song title header
        await update.message.reply_text(
            header + chunks[0],
            parse_mode="Markdown"
        )

        # Send remaining chunks if lyrics are long
        for chunk in chunks[1:3]:   # max 3 messages to avoid spam
            await update.message.reply_text(chunk)

        if len(chunks) > 3:
            await update.message.reply_text(
                "📜 _(Lyrics truncated — song is very long!)_",
                parse_mode="Markdown"
            )

    except Exception:
        await update.message.reply_text(
            "❌ Lyrics service unavailable right now.\n"
            "Try again in a moment!"
        )
