"""
Telegram Bot Downloader V3.1 (Social Only)
Fully in English. Optimized for Render.com.
"""

import os
import re
import time
import uuid
import shutil
import logging
import asyncio
import threading
import urllib.parse

import yt_dlp
import httpx
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

user_data = {}

# Platform display names + emoji
PLATFORM_META = {
    'youtube.com': ('YouTube', '▶️'),
    'youtu.be':    ('YouTube', '▶️'),
    'instagram':   ('Instagram', '📸'),
    'tiktok':      ('TikTok', '🎵'),
    'pinterest':   ('Pinterest', '📌'),
    'pin.it':      ('Pinterest', '📌'),
    'facebook':    ('Facebook', '👥'),
    'twitter':     ('Twitter X', '🐦'),
    'x.com':       ('Twitter X', '🐦'),
    'threads':     ('Threads', '🧵'),
    'spotify':     ('Spotify', '🎧'),
}

def detect_platform(url: str):
    """Returns (name, emoji) for the detected platform, or ('Unknown', '🔗')."""
    for key, meta in PLATFORM_META.items():
        if key in url.lower():
            return meta
    return ('Unknown', '🔗')

def esc(text: str) -> str:
    """Escape all MarkdownV2 reserved characters."""
    reserved = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(reserved)}])', r'\\\1', str(text))


def require_bot_token() -> str:
    """Return BOT_TOKEN or fail with a clear startup error."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Set it in the environment or .env file.")
    return BOT_TOKEN


# ========== HEALTH CHECK FOR RENDER ==========
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Social Downloader is running!")

    def log_message(self, format, *args):
        pass  # Suppress noisy HTTP logs

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()


# ========== DOWNLOAD ENGINE ==========

async def download_via_preniv(url: str, mode: str, temp_dir: str, session_id: str):
    """Use Preniv API directly for better compatibility."""
    api_map = {
        'instagram': 'https://prenivapi.vercel.app/api/igdl?url=',
        'tiktok':    'https://prenivapi.vercel.app/api/tiktok?url=',
        'pinterest': 'https://prenivapi.vercel.app/api/pinterest?url=',
        'pin.it':    'https://prenivapi.vercel.app/api/pinterest?url=',
        'facebook':  'https://prenivapi.vercel.app/api/facebookv1?url=',
        'twitter':   'https://prenivapi.vercel.app/api/twitter?url=',
        'x.com':     'https://prenivapi.vercel.app/api/twitter?url=',
        'threads':   'https://prenivapi.vercel.app/api/threads?url=',
        'spotify':   'https://prenivapi.vercel.app/api/spotify?url=',
        'youtube':   'https://prenivapi.vercel.app/api/youtube?url=',
        'youtu.be':  'https://prenivapi.vercel.app/api/youtube?url='
    }

    selected_api = None
    for key, val in api_map.items():
        if key in url.lower():
            selected_api = val
            break

    if not selected_api:
        return None, None, "This platform is not supported yet."

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Linux; Android 10; Mobile) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/90.0.4430.210 Mobile Safari/537.36'
                )
            }
            encoded_url = urllib.parse.quote(url, safe='')
            resp = await client.get(f"{selected_api}{encoded_url}", headers=headers)

            if resp.status_code != 200:
                return None, None, f"API returned status {resp.status_code}."

            data = resp.json()
            if not (data.get('status') or data.get('success')) or 'data' not in data:
                return None, None, f"API error: {data.get('message', 'Invalid response.')}"

            media_data = data['data']
            media_url = None

            downloads = media_data.get('downloads')
            if isinstance(downloads, list) and downloads:
                if mode == 'audio':
                    media_url = next(
                        (m['url'] for m in downloads if m.get('format') in ['MP3', 'M4A']),
                        downloads[0]['url']
                    )
                elif mode == 'image':
                    media_url = next(
                        (m['url'] for m in downloads if m.get('format') in ['JPG', 'PNG', 'WEBP']),
                        downloads[0]['url']
                    )
                else:
                    media_url = next(
                        (m['url'] for m in downloads if m.get('format') == 'MP4'),
                        downloads[0]['url']
                    )
            elif isinstance(downloads, dict):
                if mode == 'audio' and 'audio' in downloads:
                    media_url = downloads['audio'][0]['url']
                elif 'video' in downloads:
                    media_url = downloads['video'][0]['url']

            if not media_url:
                media_url = (
                    media_data.get('url') or
                    media_data.get('video') or
                    media_data.get('image')
                )

            if not media_url:
                media_list = media_data.get('media', [])
                if media_list:
                    if mode == 'audio':
                        media_url = next(
                            (m['url'] for m in media_list if m.get('type') == 'audio'),
                            media_list[0]['url']
                        )
                    elif mode == 'image':
                        media_url = next(
                            (m['url'] for m in media_list if m.get('type') == 'image'),
                            media_list[0]['url']
                        )
                    else:
                        media_url = media_list[0]['url']

            if not media_url:
                return None, None, "Could not extract a media link from the API response."

            file_resp = await client.get(media_url, headers=headers)
            if file_resp.status_code == 200:
                ext = 'mp4'
                if mode == 'audio': ext = 'mp3'
                elif mode == 'image': ext = 'jpg'

                filename = os.path.join(temp_dir, f"media_{session_id}.{ext}")
                with open(filename, 'wb') as f:
                    f.write(file_resp.content)
                return filename, media_data.get('title', f"media_{session_id}"), media_url
            else:
                return None, None, f"File download failed (HTTP {file_resp.status_code})."

    except Exception as e:
        return None, None, f"Request failed: {str(e)}"


def is_youtube(url):
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()


async def run_download_social(url: str, mode: str):
    session_id = str(uuid.uuid4())[:8]
    abs_download_dir = os.path.abspath(DOWNLOAD_DIR)
    temp_dir = os.path.join(abs_download_dir, session_id)
    os.makedirs(temp_dir, exist_ok=True)

    use_api_directly = is_youtube(url) or mode == 'image'

    if not use_api_directly:
        is_audio = (mode == 'audio')
        opts = {
            'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'user_agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
        }
        if os.path.exists("cookies.txt"):
            opts['cookiefile'] = 'cookies.txt'

        if is_audio:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        else:
            opts['format'] = (
                'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]'
                '/best[height<=720][ext=mp4]/best'
            )

        try:
            loop = asyncio.get_event_loop()
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                filename = ydl.prepare_filename(info)
                if is_audio:
                    filename = os.path.splitext(filename)[0] + ".mp3"

                if not os.path.exists(filename):
                    base = os.path.splitext(filename)[0]
                    for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
                        if os.path.exists(base + ext):
                            filename = base + ext
                            break

                if os.path.exists(filename):
                    return filename, info.get('title', 'Media'), None
        except Exception as e:
            logger.info(f"yt-dlp failed, falling back to Preniv: {e}")

    return await download_via_preniv(url, mode, temp_dir, session_id)


# ========== HELPERS ==========

def cleanup(path: str):
    """Remove a file's temp session directory safely."""
    try:
        temp_dir = os.path.dirname(path)
        if os.path.exists(temp_dir) and temp_dir.startswith(os.path.abspath(DOWNLOAD_DIR)):
            shutil.rmtree(temp_dir)
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")


# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = esc(update.effective_user.first_name or "there")
    await update.message.reply_text(
        f"👋 *Hey {name}\\!*\n\n"
        r"🚀 *Social Downloader * — your media grabber\." + "\n\n"
        "Just paste a link from any of these platforms:\n\n"
        "▶️  YouTube : **There are a few issues with YouTube; they will be resolved soon.**\n"
        "📸  Instagram\n"
        "🎵  TikTok\n"
        "📌  Pinterest\n"
        "🐦  Twitter X\n"
        "👥  Facebook\n"
        "🧵  Threads\n"
        "🎧  Spotify\n\n"
        r"Then choose *Video*, *Audio*, or *Image* — and you're done\." + "\n\n"
        "⚙️ Need help? Use /support",
        parse_mode="MarkdownV2"
    )


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💬 Contact Owner", url="https://t.me/Vagabondiamo")]]
    await update.message.reply_text(
        "🛠 *Support*\n\n"
        "Running into a problem? Got a feature idea?\n"
        r"Tap the button below to reach the owner directly\." + "\n\n"
        r"_Response times may vary\._",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        return

    url = url_match.group()
    platform_name, platform_emoji = detect_platform(url)
    user_data[update.message.from_user.id] = {'url': url}

    keyboard = [
        [
            InlineKeyboardButton("📹 Video", callback_data="video"),
            InlineKeyboardButton("🎵 Audio", callback_data="audio"),
            InlineKeyboardButton("🖼 Image",  callback_data="image"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]
    ]
    await update.message.reply_text(
        f"{platform_emoji} *{esc(platform_name)}* link detected\\!\n\n"
        "Choose a format to download:",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Handle cancel
    if query.data == "cancel":
        user_data.pop(query.from_user.id, None)
        await query.edit_message_text(r"🚫 *Cancelled\.*", parse_mode="MarkdownV2")
        return

    url = user_data.get(query.from_user.id, {}).get('url')
    if not url:
        await query.edit_message_text(
            r"⚠️ *Session expired\.* Please send the link again\.",
            parse_mode="MarkdownV2"
        )
        return

    choice = query.data
    MODE_LABEL = {'video': '📹 Video', 'audio': '🎵 Audio', 'image': '🖼 Image'}
    label = MODE_LABEL.get(choice, choice)

    # Step 1 — Analyzing
    url_preview = esc(url[:60] + ('…' if len(url) > 60 else ''))
    await query.edit_message_text(
        f"🔍 *Analyzing link…*\n\n`{url_preview}`",
        parse_mode="MarkdownV2"
    )

    start_time = time.time()
    file_path, title, media_url = await run_download_social(url, choice)
    extract_time = time.time() - start_time

    logger.info(f"Extraction took {extract_time:.2f}s for {url}")

    if not file_path:
        err = esc((media_url or "Unknown error")[:300])
        await query.message.reply_text(
            f"❌ *Download failed*\n\n`{err}`",
            parse_mode="MarkdownV2"
        )
        return

    # FAST PATH: send by URL (images & videos)
    if (choice == 'image' or choice == 'video') and media_url:
        try:
            await query.edit_message_text(
                f"⚡ *Sending via fast link…*\n\n"
                f"_{esc(label)}_ · extracted in {esc(f'{extract_time:.1f}')}s",
                parse_mode="MarkdownV2"
            )
            if choice == 'image':
                await query.message.reply_photo(
                    photo=media_url,
                    caption=f"🖼 {title}",
                    write_timeout=120
                )
            else:
                await query.message.reply_video(
                    video=media_url,
                    caption=f"📹 {title}",
                    write_timeout=120
                )
            cleanup(file_path)
            return
        except Exception as e:
            logger.info(f"Fast-link failed, falling back to upload: {e}")

    # SLOW PATH: upload local file
    file_size = os.path.getsize(file_path) / (1024 * 1024)

    if file_size > 50:
        await query.message.reply_text(
            f"⚠️ *File too large for Telegram*\n\n"
            f"Size: `{esc(f'{file_size:.1f}')} MB` — limit is 50 MB\\.",
            parse_mode="MarkdownV2"
        )
        cleanup(file_path)
        return

    try:
        await query.edit_message_text(
            f"📤 *Uploading…*\n\n"
            f"_{esc(label)}_ · `{esc(f'{file_size:.1f}')} MB`",
            parse_mode="MarkdownV2"
        )
        with open(file_path, 'rb') as f:
            if choice == 'audio':
                await query.message.reply_audio(
                    audio=f,
                    title=title,
                    caption=f"🎵 {title}",
                    write_timeout=120
                )
            elif choice == 'image':
                await query.message.reply_photo(
                    photo=f,
                    caption=f"🖼 {title}",
                    write_timeout=120
                )
            else:
                await query.message.reply_video(
                    video=f,
                    caption=f"📹 {title}",
                    write_timeout=120
                )
        cleanup(file_path)

    except Exception as e:
        await query.message.reply_text(
            f"❌ *Upload failed*\n\n`{esc(str(e)[:300])}`",
            parse_mode="MarkdownV2"
        )
        cleanup(file_path)


def main():
    threading.Thread(target=run_health_check, daemon=True).start()

    app = (
        ApplicationBuilder()
        .token(require_bot_token())
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(120)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
