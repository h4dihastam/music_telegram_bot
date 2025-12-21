"""
Music Telegram Bot - Entry Point (کاملاً اصلاح شده برای Render)
"""
import os
import threading
import logging
from flask import Flask

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask برای keep-alive
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def home():
    return "🎵 Music Telegram Bot is running! 🚀", 200

# ایمپورت‌های داخلی
from core.config import config
from core.database import init_db
from bot.handlers import (
    get_start_conversation_handler,
    get_settings_handlers,
)
from bot.handlers.channel import get_channel_handlers
from bot.handlers.genre import get_genre_handlers

# ساخت اپ تلگرام
from telegram.ext import Application

application = Application.builder().token(config.BOT_TOKEN).build()

# ثبت همه هندلرها
def register_handlers():
    application.add_handler(get_start_conversation_handler())
    
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

# polling در thread جدا
def run_polling():
    logger.info("🤖 شروع polling تلگرام...")
    application.run_polling(drop_pending_updates=True)

# main
def main():
    logger.info("🚀 در حال راه‌اندازی ربات...")
    
    config.validate()  # چک توکن
    init_db()
    
    register_handlers()
    setup_scheduler()
    
    # polling در background
    threading.Thread(target=run_polling, daemon=True).start()
    
    # Flask در foreground
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🌐 وب‌سرور روی پورت {port} شروع شد")
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()