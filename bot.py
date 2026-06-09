"""
Telegram Bot Downloader V3.1 (Social Only)
Fully in English. Optimized for Render.com.
"""

import os
import re
import logging
import asyncio
import threading
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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8671214452:AAHibVHglzUVRJW9EV32GMs46VOdiVpKGSs")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

user_data = {}

# ========== HEALTH CHECK FOR RENDER ==========
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Social Downloader is running!")

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ========== DOWNLOAD ENGINE ==========

def is_youtube(url):
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()

async def run_download_social(url: str, mode: str):
    is_audio = (mode == 'audio')
    is_image = (mode == 'image')
    
    opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    if is_audio:
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    elif is_image:
        opts['format'] = 'best'
        opts['writethumbnail'] = True
        opts['skip_download'] = True
    else:
        opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=not is_image))
            
            if is_image:
                # Try to get the best thumbnail
                thumbnails = info.get('thumbnails', [])
                if not thumbnails:
                    return None, None, "No image found for this link."
                
                # Sort thumbnails by preference (resolution/quality)
                # Some sites provide 'url', some 'filepath'
                best_thumb = thumbnails[-1]['url']
                # We need to download this URL
                async with httpx.AsyncClient() as client:
                    resp = await client.get(best_thumb)
                    if resp.status_code == 200:
                        filename = f"{DOWNLOAD_DIR}/image_{info.get('id', 'temp')}.jpg"
                        with open(filename, 'wb') as f:
                            f.write(resp.content)
                        return filename, info.get('title', 'Image'), None
                    else:
                        return None, None, f"Failed to download image: {resp.status_code}"

            filename = ydl.prepare_filename(info)
            if is_audio: filename = os.path.splitext(filename)[0] + ".mp3"
            
            # Post-processing check for audio/video
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm', '.mp3', '.jpg', '.png', '.webp']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            return filename, info.get('title', 'Media'), None
    except Exception as e:
        return None, None, str(e)

# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 Social Downloader V3.1\n\n"
        "Paste a link from:\n"
        "• Instagram\n"
        "• TikTok\n"
        "• Pinterest\n"
        "• Twitter/X\n"
        "• Facebook\n\n"
        "🔴 IMPORTANT: YouTube is NOT supported. 🔴\n"
        "Use /support for help or requests."
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📤 Contact Owner", url="https://t.me/Vagabondiamo")]]
    await update.message.reply_text(
        "📝 Support\n\n"
        "Click the button below to contact the owner for:\n"
        "• Reporting a problem\n"
        "• Requesting new features\n"
        "• Feedback\n\n"
        "⚠️ Remember: YouTube downloads are NOT available.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match: return

    url = url_match.group()
    if is_youtube(url):
        await update.message.reply_text(
            "❌ ERROR: YouTube downloads are strictly disabled on this bot.\n\n"
            "Please use links from Instagram, TikTok, Pinterest, Twitter, or Facebook."
        )
        return

    user_data[update.message.from_user.id] = {'url': url}
    keyboard = [[
        InlineKeyboardButton("📹 Video", callback_data="video"),
        InlineKeyboardButton("🎵 Audio", callback_data="audio"),
        InlineKeyboardButton("🖼️ Image", callback_data="image")
    ]]
    await update.message.reply_text("✅ Link detected! Choose a format:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = user_data.get(query.from_user.id, {}).get('url')
    if not url: return
    
    choice = query.data
    await query.edit_message_text(f"⏳ Downloading ({choice})...")
    
    file_path, title, error = await run_download_social(url, choice)
    if error:
        await query.message.reply_text(f"❌ Error during download:\n`{error[:200]}`")
        return

    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        await query.message.reply_text("⚠️ File too big for Telegram (>50MB).")
        os.remove(file_path)
        return

    try:
        await query.message.reply_text("📤 Uploading...")
        with open(file_path, 'rb') as f:
            if choice == 'audio': 
                await query.message.reply_audio(audio=f, title=title)
            elif choice == 'image':
                await query.message.reply_photo(photo=f, caption=title)
            else: 
                await query.message.reply_video(video=f, caption=title)
        os.remove(file_path)
    except Exception as e:
        await query.message.reply_text(f"❌ Upload error: {str(e)}")
        if os.path.exists(file_path): os.remove(file_path)

def main():
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
