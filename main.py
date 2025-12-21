"""
Music Telegram Bot - Entry Point (نسخه نهایی با همه handlerها)
"""
import os
import threading
import logging
from flask import Flask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def home():
    return "🎵 Music Telegram Bot is running! 🚀", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🌐 وب‌سرور Flask روی پورت {port} شروع شد")
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

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

# ثبت همه handlerهای اصلی
def register_all_handlers():
    # ConversationHandler برای /start
    application.add_handler(get_start_conversation_handler())
    
    # handlerهای تنظیمات، ژانر، کانال
    for handler in get_settings_handlers():
        application.add_handler(handler)
    for handler in get_channel_handlers():
        application.add_handler(handler)
    for handler in get_genre_handlers():
        application.add_handler(handler)

# error handler
async def error_handler(update, context):
    logger.error(f"خطا: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ متأسفانه یه خطایی پیش اومد!\nلطفاً دوباره امتحان کن.")

application.add_error_handler(error_handler)

# scheduler
def setup_scheduler():
    from core.scheduler import setup_scheduler
    try:
        scheduler = setup_scheduler(application.bot)
        application.bot_data['scheduler'] = scheduler
        logger.info("⏰ Scheduler راه‌اندازی شد")
    except Exception as e:
        logger.error(f"خطا در scheduler: {e}")

def main():
    logger.info("🚀 راه‌اندازی ربات...")
    
    config.validate()
    init_db()
    
    register_all_handlers()
    setup_scheduler()
    
    # Flask در background
    threading.Thread(target=run_flask, daemon=True).start()
    
    # polling در main thread
    logger.info("🤖 شروع polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()