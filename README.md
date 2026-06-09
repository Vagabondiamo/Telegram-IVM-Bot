# 🤖 Telegram Download Bot

A simple and powerful Telegram bot to download videos, audio, and images from social media (YouTube, Instagram, TikTok, Pinterest, Twitter, etc.) using `prenivdlapp-cli`.

## ✨ Features
- ✅ **Multi-platform support**: Download from YouTube, Instagram, TikTok, Pinterest, Twitter, Facebook, and more.
- 📹 **Video, Audio & Image**: Choose between downloading the video, the audio (MP3), or images.
- ⚡ **Fast**: Powered by `prenivdlapp-cli` for high-speed downloads.
- 🚀 **Free Deployment**: Ready to be deployed on Render.com or Heroku.

## 🛠️ Installation

### Local Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Vagabondiamo/telegram-download-bot.git
   cd telegram-download-bot
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your `BOT_TOKEN` in `bot.py` or as an environment variable.
4. Run the bot:
   ```bash
   python bot.py
   ```

## 🌐 Online Deployment (Render.com)
1. Create a **Web Service** on Render.
2. Connect this repository.
3. Set the **Start Command** to `python bot.py`.
4. Add your `BOT_TOKEN` in the **Environment** section.

## ⚠️ Telegram Limits
Telegram has a **50MB limit** for files sent by bots. If a video exceeds this size, the bot will notify you but won't be able to send it.

---
Created by [Vagabondiamo](https://github.com/Vagabondiamo)
