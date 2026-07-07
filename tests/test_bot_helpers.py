import os
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def install_import_stubs():
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None

    yt_dlp = types.ModuleType("yt_dlp")
    yt_dlp.YoutubeDL = object

    httpx = types.ModuleType("httpx")
    httpx.AsyncClient = object

    telegram = types.ModuleType("telegram")
    telegram.Update = object
    telegram.InlineKeyboardButton = object
    telegram.InlineKeyboardMarkup = object

    telegram_ext = types.ModuleType("telegram.ext")
    telegram_ext.ApplicationBuilder = object
    telegram_ext.MessageHandler = object
    telegram_ext.CommandHandler = object
    telegram_ext.CallbackQueryHandler = object
    telegram_ext.filters = types.SimpleNamespace(TEXT=object(), COMMAND=object())
    telegram_ext.ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=object)

    sys.modules.setdefault("dotenv", dotenv)
    sys.modules.setdefault("yt_dlp", yt_dlp)
    sys.modules.setdefault("httpx", httpx)
    sys.modules.setdefault("telegram", telegram)
    sys.modules.setdefault("telegram.ext", telegram_ext)


install_import_stubs()

import bot


class BotHelperTests(unittest.TestCase):
    def test_detect_platform_known_domains(self):
        self.assertEqual(bot.detect_platform("https://youtu.be/abc")[0], "YouTube")
        self.assertEqual(bot.detect_platform("https://www.instagram.com/p/abc")[0], "Instagram")
        self.assertEqual(bot.detect_platform("https://x.com/user/status/1")[0], "Twitter X")

    def test_detect_platform_unknown_domain(self):
        self.assertEqual(bot.detect_platform("https://example.com/video"), ("Unknown", "🔗"))

    def test_esc_escapes_markdown_v2_reserved_chars(self):
        self.assertEqual(bot.esc("a_b.c!"), r"a\_b\.c\!")

    def test_is_youtube(self):
        self.assertTrue(bot.is_youtube("https://youtube.com/watch?v=1"))
        self.assertTrue(bot.is_youtube("https://youtu.be/1"))
        self.assertFalse(bot.is_youtube("https://vimeo.com/1"))

    def test_require_bot_token_returns_configured_token(self):
        with patch.object(bot, "BOT_TOKEN", "token"):
            self.assertEqual(bot.require_bot_token(), "token")

    def test_require_bot_token_fails_clearly_when_missing(self):
        with patch.object(bot, "BOT_TOKEN", None):
            with self.assertRaisesRegex(RuntimeError, "BOT_TOKEN is missing"):
                bot.require_bot_token()


if __name__ == "__main__":
    unittest.main()
