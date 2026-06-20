# 📱 **Downloader IVM Bot**
  **[Link Bot](https://t.me/VMDownbot)**

> A Telegram bot to download videos, audio, and images from social media — fast, free, and ready to deploy.

---

## ✨ Features

| | |
|---|---|
| 📹 **Video** | Download up to 720p MP4 |
| 🎵 **Audio** | Extract MP3 at 192kbps |
| 🖼️ **Image** | Save original-quality images |
| ⚡ **Fast delivery** | Sends via direct link when possible, uploads locally as fallback |
| ❌ **Cancel anytime** | Inline cancel button before download starts |
| 🌐 **Multi-platform** | YouTube, Instagram, TikTok, Pinterest, Twitter/X, Facebook, Threads, Spotify... |

---

## 🌐 Principal Supported Platforms

| Platform | Video | Audio | Image |
|----------|:-----:|:-----:|:-----:|
| ▶️ YouTube | ✅ | ✅ | — |
| 📸 Instagram | ✅ | ✅ | ✅ |
| 🎵 TikTok | ✅ | ✅ | ✅ |
| 📌 Pinterest | ✅ | ✅| ✅ |
| 🐦 Twitter / X | ✅ | ✅ | ✅ |
| 👥 Facebook | ✅ | ✅ | ✅ |
| 🧵 Threads | ✅ | ✅ | ✅ |
| 🎧 Spotify | — | ✅ | — |

---

## 🛠️ Local Setup

**Requirements:** Python 3.10+, `ffmpeg` installed on the system.

```bash
# 1. Clone the repo
git clone https://github.com/Vagabondiamo/telegram-download-bot.git
cd telegram-download-bot

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your bot token
export BOT_TOKEN="your_token_here"
# or edit bot.py directly

# 5. Run
python bot.py
```

> Get your token from [@BotFather](https://t.me/BotFather) on Telegram.

---

## 🚀 Deploy on Render.com

1. Fork this repository
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your forked repo
4. Set the **Start Command** to:
   ```
   python bot.py
   ```
5. Under **Environment**, add:
   ```
   BOT_TOKEN = your_token_here
   ```
6. Deploy — the built-in health check keeps the service alive automatically.

---

## ⚙️ How It Works

```
User sends a link
       ↓
Bot detects platform & shows format buttons (Video / Audio / Image)
       ↓
For social video/audio → yt-dlp (with Preniv API as fallback)
For YouTube & images  → Preniv API directly
       ↓
Fast path: sends via direct URL (no upload needed)
Slow path: uploads local file if direct link fails
       ↓
File delivered. Temp files cleaned up automatically.
```

---

## ⚠️ Limits & Notes

- **50MB Telegram limit** — files larger than 50MB cannot be sent by bots. The bot will notify you.
- **Cookies** — place a `cookies.txt` file (Netscape format) in the project root to improve success rates on age-restricted or private content.
- **Spotify** — audio extraction depends on third-party API availability.

---

## 📦 Dependencies

```
python-telegram-bot
yt-dlp
httpx
python-dotenv
```

---

## 📄 License

MIT — free to use, modify, and deploy.

---

Created by:

[@Vagabondiamo](https://github.com/Vagabondiamo) [Telegram Profile](https://t.me/vagabodiamo) [Link Bot](https://t.me/VMDownbot)
