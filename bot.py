"""
Telegram Bot Downloader V2.8
Bypass YouTube "Player Response" + Multi-Instance Cobalt Fix.
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

# Istanze Cobalt più aggiornate e meno bloccate
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt.api.slashr.xyz/api/json",
    "https://api.v0.pw/api/json",
    "https://cobalt.perisic.com/api/json",
    "https://cobalt.hot-as-hell.com/api/json"
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

# ========== DOWNLOAD ENGINE ==========

async def run_download_ytdl(url: str, mode: str):
    """Download con client IOS/WEB_CREATOR (i più resistenti ora)"""
    is_audio = (mode == 'audio')
    
    opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best' if not is_audio else 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web_creator'],
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
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if is_audio: filename = os.path.splitext(filename)[0] + ".mp3"
            
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm', '.mp3']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            return filename, info.get('title', 'Media'), None
    except Exception as e:
        return None, None, str(e)

async def run_download_cobalt(url: str, mode: str):
    """Fallback su siti esterni con più tentativi"""
    is_audio = (mode == 'audio')
    payload = {"url": url, "videoQuality": "720", "isAudioOnly": is_audio, "filenameStyle": "pretty"}
    headers = {
        "Accept": "application/json", 
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    
    for api_url in COBALT_INSTANCES:
        try:
            logger.info(f"🌐 Provando Cobalt su: {api_url}")
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.post(api_url, json=payload, headers=headers, timeout=25.0)
                if response.status_code != 200: continue
                
                data = response.json()
                if data.get("status") == "stream":
                    stream_url = data.get("url")
                    title = data.get("filename", f"media_{random.randint(1000,9999)}")
                    ext = "mp3" if is_audio else "mp4"
                    file_path = os.path.join(DOWNLOAD_DIR, f"{title}.{ext}")
                    
                    async with client.get(stream_url, timeout=180.0) as r:
                        if r.status_code == 200:
                            with open(file_path, 'wb') as f: f.write(r.content)
                            return file_path, title, None
        except Exception as e:
            logger.warning(f"Errore Cobalt {api_url}: {str(e)}")
            continue
    return None, None, "Siti esterni non disponibili."

# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "✅ Cookies attivi" if os.path.exists(COOKIES_FILE) else "⚠️ Cookies mancanti"
    await update.message.reply_text(f"🚀 **Downloader V2.8**\nStato: {status}\n\nIncolla un link YouTube o Social!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if url_match:
        user_data[update.message.from_user.id] = {'url': url_match.group()}
        keyboard = [[InlineKeyboardButton("📹 Video", callback_data="video"),
                     InlineKeyboardButton("🎵 Audio", callback_data="audio")]]
        await update.message.reply_text("Scegli il formato:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = user_data.get(query.from_user.id, {}).get('url')
    if not url: return
    
    choice = query.data
    await query.edit_message_text(f"⏳ Download in corso ({choice})...")
    
    # Strategia: Prova prima Cobalt (evita blocchi IP)
    file_path, title, error = await run_download_cobalt(url, choice)
    
    # Se Cobalt fallisce, prova yt-dlp con client iOS/WebCreator
    if not file_path:
        logger.info("Cobalt fallito, provo yt-dlp con client iOS...")
        file_path, title, error = await run_download_ytdl(url, choice)

    if error and not file_path:
        await query.message.reply_text(f"❌ **Errore Finale:**\nYouTube ha bloccato anche il metodo di emergenza.\n\n`{error[:200]}`")
        return

    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        await query.message.reply_text("⚠️ File superiore a 50MB (limite Telegram).")
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

if __name__ == "__main__": main()
