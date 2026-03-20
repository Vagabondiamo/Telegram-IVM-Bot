"""
Telegram Bot Semplice per scaricare video e audio
"""

import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# ========== CONFIGURAZIONE ==========
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8671214452:AAHibVHglzUVRJW9EV32GMs46VOdiVpKGSs")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

user_data = {}

# ========== FUNZIONI ==========

async def get_media_info(url: str):
    """Ottiene info sul media"""
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Media'),
                'has_video': any(f.get('vcodec') != 'none' for f in info.get('formats', [])),
                'success': True
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def download_media(url: str, mode: str = 'video'):
    """Scarica il media"""
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == 'audio':
                new_name = filename.rsplit('.', 1)[0] + '.mp3'
                os.rename(filename, new_name)
                filename = new_name
            return filename, info.get('title', 'video'), None
    except Exception as e:
        return None, None, str(e)

async def send_file(message, file_path: str, is_audio: bool = False):
    """Invia il file"""
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        await message.reply_text(f"⚠️ File too big ({file_size//1024//1024}MB). Telegram limit is 50MB.")
        os.remove(file_path)
        return False
    
    title = os.path.basename(file_path).replace('_', ' ').replace('-', ' ')
    try:
        if is_audio:
            await message.reply_document(document=open(file_path, 'rb'), caption=f"🎵 {title}")
        else:
            await message.reply_video(video=open(file_path, 'rb'))
        os.remove(file_path)
        return True
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return False

# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    await update.message.reply_text(
        "👋 Hi! Send me a link and I'll download the file!\n\n"
        "📱 YouTube, Pinterest, Instagram, TikTok and more.\n\n"
        "🎬 Video: choose format\n"
        "🎵 Audio: direct download\n\n"
        "Use /support for issues or feature requests"
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Support command - contact owner"""
    keyboard = [
        [InlineKeyboardButton("📤 Contact Owner", url="https://t.me/Vagabondiamo")]
    ]
    
    await update.message.reply_text(
        "📝 *Support*\n\n"
        "Click the button below to contact the owner for:\n"
        "• Report a problem\n"
        "• Request new features\n"
        "• Feedback",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Cerca link
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        await update.message.reply_text("❌ Please send a valid link (https://...)")
        return
    
    url = url_match.group()
    await update.message.reply_text("🔍 Analyzing...")
    
    info = await get_media_info(url)
    if not info.get('success'):
        await update.message.reply_text(f"❌ Error: {info.get('error')}")
        return
    
    title = info.get('title', 'Media')
    user_data[user_id] = {'url': url, 'title': title}
    
    if not info.get('has_video'):
        # Audio only
        await update.message.reply_text("🎵 Downloading audio...")
        file_path, title, error = await download_media(url, 'audio')
        if error:
            await update.message.reply_text(f"❌ Error: {error}")
        else:
            await send_file(update.message, file_path, is_audio=True)
    else:
        # Video - choice
        keyboard = [
            [InlineKeyboardButton("📹 Video", callback_data="video"),
             InlineKeyboardButton("🎵 Audio", callback_data="audio")]
        ]
        await update.message.reply_text(
            f"📌 *{title}*\n\nWhat do you want to download?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i pulsanti"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    choice = query.data
    
    if user_id not in user_data or 'url' not in user_data[user_id]:
        await query.edit_message_text("❌ Session expired. Send the link again.")
        return
    
    url = user_data[user_id]['url']
    
    await query.edit_message_text("⬇️ Downloading...")
    file_path, title, error = await download_media(url, choice)
    
    if error:
        await query.message.reply_text(f"❌ Error: {error}")
    else:
        await send_file(query.message, file_path, is_audio=(choice == "audio"))

# ========== MAIN ==========

def main():
    print("🤖 Avviando bot...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot pronto!")
    app.run_polling()

if __name__ == "__main__":
    main()
