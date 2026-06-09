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
    # Map social media to preniv commands
    cmd_map = {
        'instagram': 'instagram',
        'tiktok': 'tiktok',
        'pinterest': 'pinterest',
        'facebook': 'facebook',
        'twitter': 'twitter',
        'x.com': 'twitter',
        'threads': 'threads',
        'spotify': 'spotify',
        'youtube': 'youtube',
        'youtu.be': 'youtube'
    }
    
    selected_cmd = None
    for key, val in cmd_map.items():
        if key in url.lower():
            selected_cmd = val
            break
    
    if not selected_cmd:
        return None, None, "Platform not supported by the new engine."

    # Prepare download directory
    abs_download_dir = os.path.abspath(DOWNLOAD_DIR)
    
    # We'll use a unique subdirectory to easily find the file after download
    import uuid
    session_id = str(uuid.uuid4())[:8]
    temp_dir = os.path.join(abs_download_dir, session_id)
    os.makedirs(temp_dir, exist_ok=True)

    # Command: node /home/zakaria/DVA/index.js <command> <url> -p <path>
    # Note: prenivdlapp-cli is interactive by default if no command is given, 
    # but here we use the direct subcommands.
    command = [
        "node", "/home/zakaria/DVA/index.js",
        selected_cmd, url,
        "-p", temp_dir
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            return None, None, f"Download failed: {error_msg}"

        # Find the downloaded file in temp_dir
        files = os.listdir(temp_dir)
        if not files:
            return None, None, "Download finished but no file was found."

        # Filter files by type if requested
        # preniv usually downloads the "best" available or everything.
        # We'll try to find the one that matches our mode.
        final_file = None
        if mode == 'audio':
            # Look for mp3/m4a
            for f in files:
                if f.endswith(('.mp3', '.m4a', '.wav')):
                    final_file = os.path.join(temp_dir, f)
                    break
        elif mode == 'image':
            # Look for jpg/png/webp
            for f in files:
                if f.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                    final_file = os.path.join(temp_dir, f)
                    break
        else:
            # Video or generic: prefer mp4
            for f in files:
                if f.endswith('.mp4'):
                    final_file = os.path.join(temp_dir, f)
                    break
            if not final_file:
                final_file = os.path.join(temp_dir, files[0])

        if not final_file:
            return None, None, f"Could not find a matching file for {mode}."

        return final_file, os.path.basename(final_file), None
        
    except Exception as e:
        return None, None, str(e)

# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 Social Downloader V3.1\n\n"
        "Paste a link from:\n"
        "• YouTube\n"
        "• Instagram\n"
        "• TikTok\n"
        "• Pinterest\n"
        "• Twitter/X\n"
        "• Facebook\n\n"
        "Use /support for help or requests."
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📤 Contact Owner", url="https://t.me/Vagabondiamo")]]
    await update.message.reply_text(
        "📝 Support\n\n"
        "Click the button below to contact the owner for:\n"
        "• Reporting a problem\n"
        "• Requesting new features\n"
        "• Feedback",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match: return

    url = url_match.group()
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
        
        # Cleanup: remove the file and its parent temp directory
        temp_dir = os.path.dirname(file_path)
        os.remove(file_path)
        if os.path.exists(temp_dir) and temp_dir.startswith(os.path.abspath(DOWNLOAD_DIR)):
            # Remove any other files in the same session dir
            for extra in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, extra))
            os.rmdir(temp_dir)
            
    except Exception as e:
        await query.message.reply_text(f"❌ Upload error: {str(e)}")
        if os.path.exists(file_path):
            temp_dir = os.path.dirname(file_path)
            os.remove(file_path)
            if os.path.exists(temp_dir) and temp_dir.startswith(os.path.abspath(DOWNLOAD_DIR)):
                import shutil
                shutil.rmtree(temp_dir)

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
