"""
Music Telegram Bot - Entry Point (اصلاح شده برای Render)
"""
import os
import threading
import logging
from flask import Flask

from core.config import config
from core.database import init_db
from bot.handlers import (
    get_start_conversation_handler,
    get_settings_handlers,
)
from bot.handlers.channel import get_channel_handlers
from bot.handlers.genre import get_genre_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask برای keep-alive
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def home():
    return "🎵 Music Telegram Bot is running! 🚀", 200

# تلگرام اپ - اینجا تعریف می‌شه
application = config.init_telegram_app()  # یا Application.builder().token(config.BOT_TOKEN).build()

# ثبت هندلرها
def register_handlers():
    application.add_handler(get_start_conversation_handler())
    
    # Command handlers ساده
    from telegram.ext import CommandHandler
    async def help_cmd(update, context):
        await update.message.reply_text("راهنما: /start برای شروع، /menu برای منو")
    application.add_handler(CommandHandler("help", help_cmd))
    
    for handler in get_settings_handlers():
        application.add_handler(handler)
    for handler in get_channel_handlers():
        application.add_handler(handler)
    for handler in get_genre_handlers():
        application.add_handler(handler)

# scheduler
def setup_scheduler():
    from core.scheduler import setup_scheduler
    scheduler = setup_scheduler(application.bot)
    application.bot_data['scheduler'] = scheduler

def run_polling():
    logger.info("شروع polling...")
    application.run_polling(drop_pending_updates=True)

def main():
    logger.info("🚀 راه‌اندازی ربات...")
    
    # اعتبارسنجی (BOT_TOKEN رو چک می‌کنه)
    config.validate()
    
    init_db()
    
    register_handlers()
    setup_scheduler()
    
    # polling در thread جدا
    threading.Thread(target=run_polling, daemon=True).start()
    
    # Flask در thread اصلی
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"وب‌سرور روی پورت {port}")
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()