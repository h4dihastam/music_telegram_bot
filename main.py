"""
Main entry point - ربات موزیک تلگرام
"""
import logging
import traceback
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from core.config import config
from core.database import init_db
from core.scheduler import setup_scheduler
from bot.handlers import get_start_conversation_handler, get_settings_handlers

# تنظیم logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update: Update, context):
    """مدیریت خطاها"""
    logger.exception("خطا در هندلر:")
    tb = ""
    try:
        if getattr(context, "error", None):
            tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        else:
            tb = "No traceback available"
    except Exception:
        tb = "خطا هنگام گرفتن traceback"

    logger.error("Traceback:\n%s", tb)

    # پیام کاربرپسند
    try:
        if update and getattr(update, "effective_message", None):
            await update.effective_message.reply_text(
                "❌ متأسفانه یه خطایی پیش اومد!\nلطفاً دوباره امتحان کن یا /start بزن."
            )
    except Exception:
        logger.exception("خطا هنگام ارسال پیام خطا به کاربر")


async def menu_command(update: Update, context):
    """دستور /menu"""
    from bot.handlers.settings import show_menu
    await show_menu(update, context)


async def help_command(update: Update, context):
    """دستور /help"""
    help_text = """
🎵 **راهنمای ربات موزیک روزانه**

📋 **دستورات:**
/start - شروع و تنظیمات اولیه
/menu - منوی اصلی و تنظیمات
/status - نمایش وضعیت فعلی
/help - نمایش این راهنما

🎯 **قابلیت‌ها:**
✅ انتخاب ژانر موسیقی
✅ ارسال خودکار روزانه
✅ ارسال به پیوی یا کانال
✅ دریافت متن آهنگ
✅ دانلود فایل MP3

💡 **نکات:**
• هر روز در زمان انتخابی یک آهنگ جدید دریافت می‌کنی
• می‌تونی چندین ژانر انتخاب کنی
• برای ارسال به کانال، ربات باید ادمین کانال باشه

❓ مشکلی داری؟ با /start دوباره تنظیم کن!
    """
    await update.message.reply_text(help_text)


async def status_command(update: Update, context):
    """دستور /status"""
    from bot.handlers.settings import show_status
    # ساخت یک query موقت برای استفاده از show_status
    class FakeQuery:
        async def answer(self): pass
        async def edit_message_text(self, **kwargs):
            await update.message.reply_text(**kwargs)
    
    update.callback_query = FakeQuery()
    await show_status(update, context)


def main():
    """راه‌اندازی ربات"""
    try:
        # بررسی تنظیمات
        config.validate()
        
        # راه‌اندازی دیتابیس
        logger.info("🗄️ راه‌اندازی دیتابیس...")
        init_db()
        
        # ساخت Application
        logger.info("🤖 راه‌اندازی ربات...")
        app = Application.builder().token(config.BOT_TOKEN).build()
        
        # ثبت handlers
        logger.info("📝 ثبت handlers...")
        
        # Conversation handler برای /start
        app.add_handler(get_start_conversation_handler())
        
        # دستورات ساده
        app.add_handler(CommandHandler('menu', menu_command))
        app.add_handler(CommandHandler('help', help_command))
        app.add_handler(CommandHandler('status', status_command))
        
        # Settings handlers
        for handler in get_settings_handlers():
            app.add_handler(handler)
        
        # Error handler
        app.add_error_handler(error_handler)
        
        # راه‌اندازی Scheduler
        logger.info("⏰ راه‌اندازی Scheduler...")
        scheduler = setup_scheduler(app.bot)
        
        # ذخیره scheduler در bot_data برای دسترسی بعدی
        app.bot_data['scheduler'] = scheduler
        
        # شروع ربات
        logger.info("✅ ربات شروع به کار کرد!")
        logger.info("برای توقف: Ctrl+C")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        logger.info("⛔ ربات متوقف شد (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"❌ خطای کلی: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Cleanup
        if 'scheduler' in locals():
            scheduler.shutdown()
        logger.info("👋 خداحافظ!")


if __name__ == '__main__':
    main()