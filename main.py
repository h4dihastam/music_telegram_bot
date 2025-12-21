"""
Music Telegram Bot - Entry Point (نسخه نهایی ساده برای Render)
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

# ایمپورت‌های داخلی
from core.config import config
from core.database import init_db
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

application = Application.builder().token(config.BOT_TOKEN).build()

# هندلر ساده برای /start
async def start(update, context):
    await update.message.reply_text("سلام! ربات کار می‌کنه 🎵\nژانر مورد علاقه‌ات رو انتخاب کن!")

application.add_handler(CommandHandler("start", start))

# هندلر برای پیام‌های ناشناخته
async def unknown(update, context):
    await update.message.reply_text("متوجه نشدم! از /start استفاده کن.")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

# error handler ساده
async def error_handler(update, context):
    logger.error(f"خطا: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ متأسفانه یه خطایی پیش اومد!\nلطفاً دوباره امتحان کن.")

application.add_error_handler(error_handler)

# scheduler (اختیاری، اگر کار نکرد کامنت کن)
def setup_scheduler():
    from core.scheduler import setup_scheduler
    scheduler = setup_scheduler(application.bot)
    application.bot_data['scheduler'] = scheduler

def run_polling():
    logger.info("🤖 شروع polling...")
    application.run_polling(drop_pending_updates=True)

def main():
    logger.info("🚀 راه‌اندازی...")
    
    config.validate()
    init_db()
    
    setup_scheduler()
    
    threading.Thread(target=run_polling, daemon=True).start()
    
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"وب‌سرور روی {port}")
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()