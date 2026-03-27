"""
Telegram Bot Downloader V2.7
Diagnostica avanzata + Spoofing Android per bypassare i blocchi YouTube.
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
COOKIES_FILE = "cookies.txt"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

# ========== DOWNLOAD ENGINE ==========

async def run_download_ytdl(url: str, mode: str):
    """Download con spoofing avanzato e supporto Cookies"""
    is_audio = (mode == 'audio')
    
    # Opzioni aggressive per bypassare i blocchi
    opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best' if not is_audio else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['hls', 'dash']
            }
        },
    }
    
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE

    if is_audio:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Estrazione info e download
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            
            if is_audio:
                filename = os.path.splitext(filename)[0] + ".mp3"
            
            # Controllo se il file esiste effettivamente (yt-dlp potrebbe cambiare estensione dopo il merge)
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            
            return filename, info.get('title', 'Media'), None
    except Exception as e:
        logger.error(f"Errore yt-dlp: {str(e)}")
        return None, None, str(e)

# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "✅ Cookies caricati" if os.path.exists(COOKIES_FILE) else "⚠️ Cookies mancanti"
    await update.message.reply_text(f"🚀 **Downloader V2.7**\nStato: {status}\n\nMandami un link!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if url_match:
        user_data[update.message.from_user.id] = {'url': url_match.group()}
        keyboard = [[InlineKeyboardButton("📹 Video", callback_data="video"),
                     InlineKeyboardButton("🎵 Audio", callback_data="audio")]]
        await update.message.reply_text("Cosa vuoi scaricare?", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = user_data.get(query.from_user.id, {}).get('url')
    if not url:
        await query.edit_message_text("❌ Sessione scaduta. Reinvia il link.")
        return
    
    choice = query.data
    await query.edit_message_text(f"⏳ Download in corso ({choice})...")
    
    file_path, title, error = await run_download_ytdl(url, choice)

    if error:
        # Mostriamo l'errore REALE per capire cosa succede
        await query.message.reply_text(f"❌ **Errore tecnico:**\n`{error[:300]}`")
        return

    if not file_path or not os.path.exists(file_path):
        await query.message.reply_text("❌ File non trovato dopo il download.")
        return

    # Limite 50MB
    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        await query.message.reply_text(f"⚠️ File troppo grande ({os.path.getsize(file_path)//1024//1024}MB).")
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
