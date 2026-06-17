# ============================================================
#  handlers/media.py
#  /meme    — Random meme from Reddit
#  /gif     — Random GIF via Tenor
#  /movie   — Movie info from OMDB API
#  /anime   — Anime info from Jikan (MyAnimeList) API
#  /youtube — YouTube search link
#  /spotify — Spotify search link
# ============================================================

import requests
import os
import random
from telegram import Update
from telegram.ext import ContextTypes

OMDB_API_KEY   = os.environ.get("OMDB_API_KEY", "")   # free at omdbapi.com
# Tenor API discontinued Jan 2026 — using Giphy CDN direct links instead (no API key needed)

# ── /meme ─────────────────────────────────────────────────

MEME_SUBREDDITS = [
    "memes", "dankmemes", "ProgrammerHumor", "technicallythetruth",
    "me_irl", "funny", "IndianDankMemes", "196",
]


async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/meme [subreddit] — Fetch a random meme."""
    await update.message.chat.send_action("upload_photo")

    # Allow /meme ProgrammerHumor etc
    subreddit = context.args[0] if context.args else random.choice(MEME_SUBREDDITS)

    try:
        # meme-api.com — purpose-built free meme API, no auth needed
        url  = f"https://meme-api.com/gimme/{subreddit}"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data.get("nsfw") or not data.get("url"):
            # retry with safe subreddit
            url  = "https://meme-api.com/gimme/memes"
            resp = requests.get(url, timeout=10)
            data = resp.json()

        title     = data.get("title", "😂 Meme")
        img_url   = data.get("url", "")
        ups       = data.get("ups", 0)
        sub_name  = data.get("subreddit", subreddit)
        post_link = data.get("postLink", "")

        if not img_url:
            await update.message.reply_text("😅 Couldn't fetch a meme. Try again!")
            return

        caption = f"😂 {title[:180]}\n\n👍 {ups:,} upvotes · r/{sub_name}"

        try:
            await update.message.reply_photo(
                photo=img_url,
                caption=caption,
            )
        except Exception:
            # If image send fails, send link
            await update.message.reply_text(f"{caption}\n\n🔗 {post_link or img_url}")

    except Exception as e:
        await update.message.reply_text(
            f"😅 Meme service unavailable right now. Try again!\n"
            f"Or specify a subreddit: `/meme ProgrammerHumor`",
            parse_mode="Markdown"
        )


# ── /gif ─────────────────────────────────────────────────

# ── /movie ────────────────────────────────────────────────

async def movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/movie <title> — Movie info, rating, cast from OMDB."""
    if not context.args:
        await update.message.reply_text(
            "🎬 *Movie Info*\n\n"
            "`/movie Interstellar`\n"
            "`/movie RRR`\n"
            "`/movie Inception`\n"
            "`/movie 3 Idiots`\n"
            "`/movie Avengers Endgame`",
            parse_mode="Markdown"
        )
        return

    title = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        if not OMDB_API_KEY:
            # Use free OMDB without key (limited)
            url = f"https://www.omdbapi.com/?t={requests.utils.quote(title)}&apikey=trilogy"
        else:
            url = f"https://www.omdbapi.com/?t={requests.utils.quote(title)}&apikey={OMDB_API_KEY}"

        resp = requests.get(url, timeout=8)
        data = resp.json()

        if data.get("Response") == "False":
            await update.message.reply_text(
                f"❌ Movie '{title}' not found.\n\n"
                "Try the exact English title, e.g. `/movie 3 Idiots`",
                parse_mode="Markdown"
            )
            return

        m_title  = data.get("Title", title)
        year     = data.get("Year", "N/A")
        rating   = data.get("imdbRating", "N/A")
        genre    = data.get("Genre", "N/A")
        director = data.get("Director", "N/A")
        cast     = data.get("Actors", "N/A")
        plot     = data.get("Plot", "N/A")
        runtime  = data.get("Runtime", "N/A")
        language = data.get("Language", "N/A")
        poster   = data.get("Poster", "")
        awards   = data.get("Awards", "N/A")

        text = (
            f"🎬 *{m_title}* ({year})\n\n"
            f"⭐ IMDB: *{rating}/10*\n"
            f"🎭 Genre: {genre}\n"
            f"⏱ Runtime: {runtime}\n"
            f"🌐 Language: {language}\n"
            f"🎬 Director: {director}\n"
            f"👥 Cast: {cast}\n\n"
            f"📖 *Plot:*\n_{plot}_\n\n"
            f"🏆 {awards}"
        )

        if poster and poster != "N/A":
            await update.message.reply_photo(
                photo=poster,
                caption=text,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("❌ Movie database unavailable. Try again!")


# ── /anime ────────────────────────────────────────────────

async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/anime <title> — Anime info from MyAnimeList via Jikan API."""
    if not context.args:
        await update.message.reply_text(
            "🎌 *Anime Info*\n\n"
            "`/anime Naruto`\n"
            "`/anime Attack on Titan`\n"
            "`/anime Death Note`\n"
            "`/anime One Piece`\n"
            "`/anime Demon Slayer`",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args)
    await update.message.chat.send_action("typing")

    try:
        url  = "https://api.jikan.moe/v4/anime"
        resp = requests.get(url, params={"q": query, "limit": 1}, timeout=10)
        data = resp.json()

        results = data.get("data", [])
        if not results:
            await update.message.reply_text(f"❌ Anime '{query}' not found on MAL.")
            return

        a = results[0]

        a_title    = a.get("title_english") or a.get("title", query)
        a_jp       = a.get("title_japanese", "")
        score      = a.get("score", "N/A")
        episodes   = a.get("episodes", "?")
        status     = a.get("status", "N/A")
        rating     = a.get("rating", "N/A")
        studios    = ", ".join(s["name"] for s in a.get("studios", []))
        genres     = ", ".join(g["name"] for g in a.get("genres", []))
        synopsis   = a.get("synopsis", "No synopsis available.")[:300] + "..."
        aired      = a.get("aired", {}).get("string", "N/A")
        image_url  = a.get("images", {}).get("jpg", {}).get("image_url", "")
        mal_url    = a.get("url", "")

        text = (
            f"🎌 *{a_title}*\n"
            f"_{a_jp}_\n\n"
            f"⭐ MAL Score: *{score}/10*\n"
            f"📺 Episodes: {episodes}\n"
            f"📅 Aired: {aired}\n"
            f"🟢 Status: {status}\n"
            f"🔞 Rating: {rating}\n"
            f"🎬 Studios: {studios or 'N/A'}\n"
            f"🏷 Genres: {genres or 'N/A'}\n\n"
            f"📖 *Synopsis:*\n_{synopsis}_\n\n"
            f"🔗 [View on MAL]({mal_url})"
        )

        if image_url:
            await update.message.reply_photo(
                photo=image_url,
                caption=text,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

    except Exception:
        await update.message.reply_text("❌ Anime database unavailable. Try again!")


# ── /youtube ─────────────────────────────────────────────

async def youtube_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/youtube <search query> — Get YouTube search link."""
    if not context.args:
        await update.message.reply_text(
            "📺 *YouTube Search*\n\n"
            "`/youtube lofi music`\n"
            "`/youtube python tutorial`\n"
            "`/youtube Arijit Singh songs`",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args)
    encoded = requests.utils.quote(query)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"

    await update.message.reply_text(
        f"📺 *YouTube Search: {query}*\n\n"
        f"🔗 [Click to search on YouTube]({search_url})\n\n"
        f"_Tap the link to open YouTube results!_",
        parse_mode="Markdown",
        disable_web_page_preview=False
    )


# ── /spotify ─────────────────────────────────────────────

async def spotify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/spotify <song or artist> — Search Spotify."""
    if not context.args:
        await update.message.reply_text(
            "🎵 *Spotify Search*\n\n"
            "`/spotify Tum Hi Ho`\n"
            "`/spotify Arijit Singh`\n"
            "`/spotify lofi chill mix`",
            parse_mode="Markdown"
        )
        return

    query    = " ".join(context.args)
    encoded  = requests.utils.quote(query)
    spot_url = f"https://open.spotify.com/search/{encoded}"

    await update.message.reply_text(
        f"🎵 *Spotify: {query}*\n\n"
        f"🔗 [Search on Spotify]({spot_url})\n\n"
        f"_Tap to open in Spotify!_",
        parse_mode="Markdown",
        disable_web_page_preview=False
    )
