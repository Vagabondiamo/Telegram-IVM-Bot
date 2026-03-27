"""
Telegram Bot Downloader V3.0 (Social Only)
Specializzato per: Instagram, TikTok, Pinterest, Twitter/X e altri social.
YouTube disabilitato per evitare blocchi IP su Render.
"""

import os
import re
import logging
import asyncio
import threading
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

user_data = {}

# ========== HEALTH CHECK PER RENDER ==========
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Social Downloader is running!")

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ========== DOWNLOAD ENGINE (SOCIAL) ==========

def is_youtube(url):
    """Rileva se il link è YouTube"""
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()

async def run_download_social(url: str, mode: str):
    """Download per i social tramite yt-dlp locale"""
    is_audio = (mode == 'audio')
    
    opts = {
        # Max 720p per stare sotto i 50MB di Telegram
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best' if not is_audio else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    if is_audio:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            
            if is_audio:
                filename = os.path.splitext(filename)[0] + ".mp3"
            
            # Gestione cambio estensione post-merge
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            
            return filename, info.get('title', 'Media'), None
    except Exception as e:
        return None, None, str(e)

# ========== HANDLERS TELEGRAM ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 Social Downloader V3.0\n\n"
        "Incolla un link da:\n"
        "• Instagram\n"
        "• TikTok\n"
        "• Pinterest\n"
        "• Twitter/X\n"
        "• Facebook\n\n"
        "⚠️ Nota: YouTube non è supportato su questo bot."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match: return
    
    url = url_match.group()
    
    # Blocco YouTube esplicito
    if is_youtube(url):
        await update.message.reply_text("❌ Mi dispiace, il download da YouTube è disabilitato su questo server a causa dei blocchi IP.")
        return

    user_data[update.message.from_user.id] = {'url': url}
    keyboard = [[InlineKeyboardButton("📹 Video", callback_data="video"),
                 InlineKeyboardButton("🎵 Audio", callback_data="audio")]]
    await update.message.reply_text("✅ Link rilevato! Scegli cosa scaricare:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = user_data.get(query.from_user.id, {}).get('url')
    if not url: return
    
    choice = query.data
    await query.edit_message_text(f"⏳ Download social in corso ({choice})...")
    
    file_path, title, error = await run_download_social(url, choice)

    if error:
        await query.message.reply_text(f"❌ Errore durante il download:\n`{error[:200]}`")
        return

    # Limite 50MB
    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        await query.message.reply_text("⚠️ Il file supera i 50MB (limite di Telegram per i bot).")
        os.remove(file_path)
        return

    try:
        await query.message.reply_text("📤 Invio in corso...")
        with open(file_path, 'rb') as f:
            if choice == 'audio': await query.message.reply_audio(audio=f, title=title)
            else: await query.message.reply_video(video=f, caption=title)
        os.remove(file_path)
    except Exception as e:
        await query.message.reply_text(f"❌ Errore nell'invio: {str(e)}")
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
