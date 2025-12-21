"""
Entry point for Music Telegram Bot
"""
import os
import threading
import logging
from flask import Flask

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("music_bot")

# simple health-check Flask app
flask_app = Flask(__name__)

@flask_app.route("/")
@flask_app.route("/health")
def home():
    return "🎵 Music Telegram Bot is running! 🚀", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🌐 Flask webserver starting on port {port}")
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

# Telegram bot imports (lazy to avoid import-time side effects)
def import_bot_components():
    from core.config import config
    from core.database import init_db
    from bot.handlers import (
        get_start_conversation_handler,
        get_settings_handlers,
    )
    from bot.handlers.channel import get_channel_handlers
    from bot.handlers.genre import get_genre_handlers
    return config, init_db, get_start_conversation_handler, get_settings_handlers, get_channel_handlers, get_genre_handlers

def register_all_handlers(application, get_start_conversation_handler, get_settings_handlers, get_channel_handlers, get_genre_handlers):
    application.add_handler(get_start_conversation_handler())
    for handler in get_settings_handlers():
        application.add_handler(handler)
    for handler in get_channel_handlers():
        application.add_handler(handler)
    for handler in get_genre_handlers():
        application.add_handler(handler)

async def error_handler(update, context):
    logger.error(f"خطا: {context.error}")
    if update and getattr(update, "effective_message", None):
        await update.effective_message.reply_text(
            "❌ متأسفانه یه خطایی پیش اومد!\nلطفاً دوباره امتحان کن."
        )

def setup_scheduler(application):
    try:
        from core.scheduler import setup_scheduler
        scheduler = setup_scheduler(application.bot)
        application.bot_data['scheduler'] = scheduler
        logger.info("⏰ Scheduler راه‌اندازی شد")
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی scheduler: {e}")

def main():
    logger.info("🚀 راه‌اندازی ربات...")
    config, init_db, get_start_conversation_handler, get_settings_handlers, get_channel_handlers, get_genre_handlers = import_bot_components()
    config.validate()
    init_db()

    # build telegram application lazily
    from telegram.ext import Application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # register handlers and error handler
    register_all_handlers(application, get_start_conversation_handler, get_settings_handlers, get_channel_handlers, get_genre_handlers)
    application.add_error_handler(error_handler)

    # scheduler
    setup_scheduler(application)

    # run flask in background
    threading.Thread(target=run_flask, daemon=True).start()

    # start polling
    logger.info("🤖 شروع polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()