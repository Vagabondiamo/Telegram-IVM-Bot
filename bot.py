"""
Telegram Bot Downloader V2.4
Multi-fallback: Cobalt (Siti Esterni) -> yt-dlp locale.
"""

import os
import re
import logging
import asyncio
import threading
import random
import httpx
import yt_dlp
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

# ========== CONFIGURAZIONE ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8671214452:AAHibVHglzUVRJW9EV32GMs46VOdiVpKGSs")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Lista aggiornata di istanze Cobalt (Siti esterni di download)
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt-api.v0.pw/api/json",
    "https://api.cobalt.red/api/json",
    "https://cobalt.api.slashr.xyz/api/json",
    "https://cobalt.perisic.com/api/json"
]

user_data = {}

# ========== HEALTH CHECK ==========
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ========== STRUMENTI DI DOWNLOAD ==========

def is_youtube(url):
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()

async def run_download_cobalt(url: str, mode: str):
    """Tentativo tramite siti esterni (Cobalt)"""
    is_audio = (mode == 'audio')
    payload = {
        "url": url, 
        "videoQuality": "720", 
        "filenameStyle": "pretty",
        "isAudioOnly": is_audio
    }
    # User-Agent reale per non essere bloccati da Cobalt
    headers = {
        "Accept": "application/json", 
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for api_url in COBALT_INSTANCES:
        try:
            logger.info(f"Tentativo YouTube via: {api_url}")
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json=payload, headers=headers, timeout=20.0)
                data = response.json()
                
                if data.get("status") == "stream":
                    stream_url = data.get("url")
                    ext = "mp3" if is_audio else "mp4"
                    title = data.get("filename", f"media_{random.randint(1000,9999)}")
                    file_path = os.path.join(DOWNLOAD_DIR, f"{title}.{ext}")
                    
                    async with client.get(stream_url, timeout=120.0) as r:
                        if r.status_code == 200:
                            with open(file_path, 'wb') as f:
                                f.write(r.content)
                            return file_path, title, None
                else:
                    logger.warning(f"Cobalt ({api_url}) ha risposto: {data.get('text', 'No error text')}")
        except Exception as e:
            logger.warning(f"Errore istanza {api_url}: {str(e)}")
            continue
    return None, None, "Siti esterni non disponibili."

async def run_download_ytdl(url: str, mode: str):
    """Tentativo locale tramite yt-dlp"""
    opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if mode != 'audio' else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if os.path.exists("cookies.txt"):
        opts['cookiefile'] = "cookies.txt"
    if mode == 'audio':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if mode == 'audio': filename = os.path.splitext(filename)[0] + ".mp3"
            
            if not os.path.exists(filename):
                for e in ['.mp4', '.mkv', '.webm', '.mp3']:
                    if os.path.exists(os.path.splitext(filename)[0] + e):
                        filename = os.path.splitext(filename)[0] + e
                        break
            return filename, info.get('title', 'Media'), None
    except Exception as e:
        return None, None, str(e)

# ========== HANDLERS TELEGRAM ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **Downloader V2.4 pronto!**\nIncolla un link per scaricare video o audio.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match: return
    
    url = url_match.group()
    user_data[update.message.from_user.id] = {'url': url}
    
    keyboard = [[InlineKeyboardButton("📹 Video", callback_data="video"),
                 InlineKeyboardButton("🎵 Audio", callback_data="audio")]]
    await update.message.reply_text("✅ Link rilevato! Scegli il formato:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data:
        await query.edit_message_text("❌ Sessione scaduta.")
        return
        
    choice = query.data
    url = user_data[user_id]['url']
    await query.edit_message_text(f"⏳ Download in corso ({choice})...")
    
    # 1. Prova prima con i siti esterni (Cobalt)
    file_path, title, error = await run_download_cobalt(url, choice)
    
    # 2. Se fallisce, prova yt-dlp locale (ottimo se hai caricato i cookies)
    if not file_path:
        logger.info("Siti esterni falliti, provo download locale...")
        file_path, title, error = await run_download_ytdl(url, choice)
    
    if error and not file_path:
        await query.message.reply_text(f"❌ Errore: {error[:200]}\n\n💡 Se è YouTube, i server sono bloccati. Carica un file cookies.txt per risolvere.")
        return

    # Limite 50MB
    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        await query.message.reply_text("⚠️ File troppo grande (>50MB).")
        os.remove(file_path)
        return

    try:
        await query.message.reply_text("📤 Invio...")
        with open(file_path, 'rb') as f:
            if choice == 'audio': await query.message.reply_audio(audio=f, title=title)
            else: await query.message.reply_video(video=f, caption=title)
        os.remove(file_path)
    except Exception as e:
        await query.message.reply_text(f"❌ Errore invio: {str(e)}")
        if os.path.exists(file_path): os.remove(file_path)

def main():
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
