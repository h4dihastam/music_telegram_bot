"""
ربات موزیک تلگرام - نقطه ورود اصلی (اصلاح شده)
"""
import logging
import traceback
import sys
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    Defaults
)
import pytz

from core.config import Config
from core.database import init_db
from core.scheduler import setup_scheduler  # حالا با JobQueue
from bot.handlers import get_start_conversation_handler, get_settings_handlers

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context):
    """مدیریت خطاهای غیرمنتظره"""
    logger.error("❌ خطای داخلی ربات:", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ متأسفانه مشکلی در پردازش پیش آمد. لطفاً دوباره تلاش کنید.")

async def main():
    """شروع به کار ربات"""
    try:
        # ۱. آماده‌سازی دیتابیس
        init_db()
        logger.info("🗄️ دیتابیس آماده شد.")

        # ۲. تنظیمات پیش‌فرض (منطقه زمانی)
        defaults = Defaults(tzinfo=pytz.timezone(Config.DEFAULT_TIMEZONE))

        # ۳. ساخت اپلیکیشن (با job_queue فعال)
        app = ApplicationBuilder().token(Config.BOT_TOKEN).defaults(defaults).build()

        # ۴. اضافه کردن هندلرها
        app.add_handler(get_start_conversation_handler())
        
        for handler in get_settings_handlers():
            app.add_handler(handler)
        
        app.add_error_handler(error_handler)

        # ۵. راه‌اندازی Scheduler با JobQueue
        scheduler = setup_scheduler(app.job_queue)  # حالا job_queue داخلی
        app.bot_data['scheduler'] = scheduler

        logger.info("✅ ربات آنلاین شد!")
        
        # ۶. اجرای ربات (Polling)
        await app.run_polling(
            drop_pending_updates=True, 
            allowed_updates=Update.ALL_TYPES
        )

    except Exception as e:
        logger.error(f"❌ خطای بحرانی در متد اصلی: {e}")
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ ربات توسط کاربر متوقف شد.")