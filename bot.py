"""
Telegram Bot Downloader Avanzato (v2.1)
Supporta: YouTube, Instagram, TikTok, Pinterest e altro.
Ottimizzato per: Render.com (Health Check + Docker)
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

# Carica variabili d'ambiente da .env (se presente)
load_dotenv()

# Configurazione Logging
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

# ========== HEALTH CHECK PER RENDER ==========

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"✅ Health check server started on port {port}")
    server.serve_forever()

# ========== YT-DLP UTILS ==========

def get_ytdl_opts(mode='video'):
    """Opzioni per yt-dlp ottimizzate per bypassare i blocchi"""
    
    if mode == 'video_lite':
        format_str = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
    elif mode == 'audio':
        format_str = 'bestaudio/best'
    else: # video standard (best)
        format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

    opts = {
        'format': format_str,
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4' if 'video' in mode else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['hls', 'dash']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if mode == 'audio' else [],
    }
    
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
        
    return opts

async def extract_info(url: str):
    """Estrae informazioni sul video senza scaricarlo"""
    opts = {
        'quiet': True, 
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
        
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            return {
                'title': info.get('title', 'Media'),
                'success': True
            }
    except Exception as e:
        # Fallback semplice per siti non-YouTube
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                return {'title': info.get('title', 'Media'), 'success': True}
        except:
            logger.error(f"❌ Errore estrazione info: {str(e)}")
            return {'success': False, 'error': str(e)}

async def run_download_ytdl(url: str, mode: str):
    """Esegue il download tramite yt-dlp"""
    opts = get_ytdl_opts(mode)
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            
            if mode == 'audio':
                filename = os.path.splitext(filename)[0] + ".mp3"
            
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in ['.mp4', '.mkv', '.webm']:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
                
            return filename, info.get('title', 'video'), None
    except Exception as e:
        logger.error(f"❌ Errore yt-dlp: {str(e)}")
        return None, None, str(e)

# ========== COBALT API (FALLBACK / VELOCE) ==========

async def run_download_cobalt(url: str):
    """Scarica media usando l'API di Cobalt (molto utile online)"""
    api_url = "https://api.cobalt.tools/api/json"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"url": url, "videoQuality": "720", "filenameStyle": "pretty"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers, timeout=30.0)
            data = response.json()
            
            if data.get("status") == "stream":
                stream_url = data.get("url")
                title = data.get("filename", f"video_{random.randint(1000,9999)}")
                file_path = os.path.join(DOWNLOAD_DIR, f"{title}.mp4")
                
                async with client.get(stream_url, timeout=120.0) as r:
                    with open(file_path, 'wb') as f:
                        f.write(r.content)
                return file_path, title, None
            else:
                return None, None, data.get("text", "Cobalt error")
    except Exception as e:
        return None, None, f"Cobalt error: {str(e)}"

# ========== TELEGRAM HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **Downloader Bot Online** pronto!\n\n"
        "Incolla un link (YouTube, Instagram, TikTok, ecc.) e scegli il formato.\n\n"
        "✨ **Supporto:** @Vagabondiamo"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match: return
        
    url = url_match.group()
    sent_msg = await update.message.reply_text("🔍 Analisi del link...")
    
    info = await extract_info(url)
    if not info['success']:
        await sent_msg.edit_text(f"❌ **Errore nell'analisi:**\n`{info['error']}`")
        return

    user_data[update.message.from_user.id] = {'url': url, 'title': info['title']}
    
    keyboard = [
        [InlineKeyboardButton("📹 Video HD", callback_data="video"),
         InlineKeyboardButton("📹 Video Lite (720p)", callback_data="video_lite")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio")]
    ]
    await sent_msg.edit_text(
        f"✅ **Trovato:** {info['title']}\n\nCosa vuoi scaricare?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in user_data:
        await query.edit_message_text("❌ Sessione scaduta. Reinvia il link.")
        return
        
    choice = query.data
    url = user_data[user_id]['url']
    await query.edit_message_text(f"⏳ Download in corso ({choice})...")
    
    # Se video, prova prima Cobalt (più veloce), se fallisce o se è audio usa yt-dlp
    file_path, title, error = None, None, None
    if choice == 'video' or choice == 'video_lite':
        file_path, title, error = await run_download_cobalt(url)
        if error: # Se Cobalt fallisce, usa yt-dlp come backup
            logger.info(f"Cobalt fallito, uso yt-dlp: {error}")
            file_path, title, error = await run_download_ytdl(url, choice)
    else: # Audio
        file_path, title, error = await run_download_ytdl(url, choice)
    
    if error:
        await query.message.reply_text(f"❌ Errore durante il download:\n`{error}`")
        return

    # Controllo dimensione file (Telegram limit: 50MB)
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    if file_size > 50:
        await query.message.reply_text(f"⚠️ Il file è troppo grande ({file_size:.1f}MB). Limite bot: 50MB.")
        os.remove(file_path)
        return

    try:
        await query.message.reply_text("📤 Invio in corso...")
        with open(file_path, 'rb') as f:
            if choice == 'audio':
                await query.message.reply_audio(audio=f, title=title)
            else:
                await query.message.reply_video(video=f, caption=title)
        os.remove(file_path)
    except Exception as e:
        await query.message.reply_text(f"❌ Errore nell'invio: {str(e)}")
        if os.path.exists(file_path): os.remove(file_path)

# ========== MAIN ==========

def main():
    logger.info("🤖 Avvio del bot...")
    
    # Avvia Health Check in background per Render
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("✅ Bot pronto e in ascolto!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
