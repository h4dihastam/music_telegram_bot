"""
ربات موزیک تلگرام - نقطه ورود اصلی
"""
import logging
import traceback
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from core.config import config
from core.database import init_db
from core.scheduler import setup_scheduler
from bot.handlers import get_start_conversation_handler, get_settings_handlers

# تنظیم logging با فارسی
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def error_handler(update: Update, context):
    """مدیریت خطاها"""
    logger.error("❌ خطا رخ داد!", exc_info=context.error)
    
    # لاگ کامل
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    logger.error(f"📋 جزئیات خطا:\n{tb_string}")
    
    # پیام به کاربر
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ متأسفانه یه خطایی پیش اومد!\n"
                "لطفاً دوباره امتحان کن یا /start بزن."
            )
    except Exception as e:
        logger.error(f"❌ خطا در ارسال پیام خطا: {e}")


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
    
    class FakeQuery:
        async def answer(self): 
            pass
        async def edit_message_text(self, **kwargs):
            await update.message.reply_text(**kwargs)
    
    update.callback_query = FakeQuery()
    await show_status(update, context)


def main():
    """راه‌اندازی ربات"""
    try:
        logger.info("🚀 راه‌اندازی ربات...")
        
        # بررسی تنظیمات
        config.validate()
        
        # راه‌اندازی دیتابیس
        logger.info("🗄️ راه‌اندازی دیتابیس...")
        init_db()
        
        # ساخت Application
        logger.info("🤖 ساخت Application...")
        app = Application.builder().token(config.BOT_TOKEN).build()
        
        # ثبت handlers
        logger.info("📝 ثبت handlers...")
        
        # Conversation handler برای /start
        start_handler = get_start_conversation_handler()
        app.add_handler(start_handler)
        
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
        app.bot_data['scheduler'] = scheduler
        
        # شروع ربات
        logger.info("✅ ربات شروع به کار کرد!")
        logger.info("📡 در حال گوش دادن به پیام‌ها...")
        logger.info("⏹️ برای توقف: Ctrl+C")
        
        # اجرای polling
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # نادیده گرفتن پیام‌های قدیمی
        )
        
    except KeyboardInterrupt:
        logger.info("⛔ ربات متوقف شد (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"❌ خطای کلی: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Cleanup
        if 'scheduler' in locals():
            logger.info("🧹 در حال پاکسازی...")
            scheduler.shutdown()
        logger.info("👋 خداحافظ!")


if __name__ == '__main__':
    main()