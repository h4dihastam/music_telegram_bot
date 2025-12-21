"""
Music Telegram Bot - Entry Point (نسخه نهایی برای Render - polling در main thread)
"""
import os
import threading
import logging
from flask import Flask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask برای keep-alive
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
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ساخت اپ تلگرام
application = Application.builder().token(config.BOT_TOKEN).build()

# هندلر ساده برای تست
async def start(update, context):
    await update.message.reply_text("🎉 ایول! ربات روی Render کار می‌کنه!\nحالا می‌تونیم handlerهای اصلی رو اضافه کنیم.")

application.add_handler(CommandHandler("start", start))

async def unknown(update, context):
    await update.message.reply_text("🤔 دستور ناشناخته! /start بزن.")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

async def error_handler(update, context):
    logger.error(f"خطا: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ خطایی پیش اومد! دوباره امتحان کن.")

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
    
    config.validate()  # چک توکن
    init_db()
    
    setup_scheduler()
    
    # Flask در thread جدا
    threading.Thread(target=run_flask, daemon=True).start()
    
    # polling در main thread (مهم!)
    logger.info("🤖 شروع polling تلگرام در main thread...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()