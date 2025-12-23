#!/usr/bin/env python3
"""
ربات موزیک تلگرام - Fixed Version
"""
import logging
import sys
import os
from telegram import Update
from telegram.ext import Application, CommandHandler

from core.config import config
from core.database import init_db
from core.scheduler import setup_scheduler
from bot.handlers import get_start_conversation_handler, get_settings_handlers

# تنظیم logging با جزئیات بیشتر
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8') if os.path.exists('/app') else logging.StreamHandler()
    ]
)

# کاهش noise از کتابخانه‌ها
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context):
    """مدیریت خطاها"""
    logger.error("❌ خطا رخ داد!", exc_info=context.error)
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ متأسفانه یه مشکلی پیش اومد!\n"
                "لطفاً دوباره امتحان کن یا /start بزن."
            )
    except Exception as e:
        logger.error(f"خطا در ارسال پیام خطا: {e}")


async def menu_command(update: Update, context):
    """دستور /menu"""
    from bot.handlers.settings import show_menu
    await show_menu(update, context)


async def help_command(update: Update, context):
    """دستور /help"""
    help_text = """
🎵 <b>راهنمای ربات موزیک روزانه</b>

📋 <b>دستورات:</b>
/start - شروع و تنظیمات
/menu - منوی اصلی
/status - وضعیت فعلی
/help - این راهنما

🎯 <b>قابلیت‌ها:</b>
✅ انتخاب ژانر موسیقی
✅ ارسال خودکار روزانه
✅ ارسال به پیوی یا کانال
✅ دریافت متن آهنگ
✅ دانلود MP3

💡 <b>نکات:</b>
- هر روز در زمان انتخابی موزیک میگیری
- می‌تونی چند ژانر انتخاب کنی
- برای کانال، ربات باید ادمین باشه
    """
    await update.message.reply_text(
        help_text,
        parse_mode='HTML'
    )


async def status_command(update: Update, context):
    """دستور /status"""
    # نکته: به جای استفاده از show_status که برای دکمه‌ها طراحی شده،
    # اینجا یک پیام ساده می‌فرستیم یا باید تابع show_status را اصلاح کنید
    # که به update.callback_query وابسته نباشد.
    
    from core.database import SessionLocal, UserSettings
    
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        if not settings:
            await update.message.reply_text("❌ تنظیماتی یافت نشد. /start را بزنید.")
            return

        # نمایش وضعیت به صورت متن ساده (بدون دکمه‌های شیشه‌ای پیچیده)
        status_text = (
            f"📊 <b>وضعیت ربات شما:</b>\n\n"
            f"⏰ زمان ارسال: {settings.schedule_time}\n"
            f"🎵 ژانرها: {settings.genres if settings.genres else 'همه'}\n"
            f"active: {'✅' if settings.is_active else '❌'}"
        )
        await update.message.reply_text(status_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        await update.message.reply_text("خطایی در دریافت وضعیت رخ داد.")
    finally:
        db.close()


async def post_init(application: Application):
    """بعد از راه‌اندازی"""
    logger.info("🤖 ربات آماده است!")
    logger.info(f"👤 Bot Username: @{application.bot.username}")


def main():
    """راه‌اندازی ربات"""
    try:
        logger.info("="*60)
        logger.info("🚀 شروع راه‌اندازی ربات موزیک...")
        logger.info("="*60)
        
        # بررسی تنظیمات
        logger.info("⚙️ بررسی تنظیمات...")
        config.validate()
        
        # چک توکن
        if not config.BOT_TOKEN:
            logger.error("❌ BOT_TOKEN موجود نیست!")
            logger.error("💡 توکن رو در Environment Variables تنظیم کن")
            sys.exit(1)
        
        logger.info("✅ تنظیمات OK")
        
        # دیتابیس
        logger.info("🗄️ راه‌اندازی دیتابیس...")
        init_db()
        logger.info("✅ دیتابیس OK")
        
        # ساخت Application
        logger.info("🤖 ساخت Application...")
        app = Application.builder().token(config.BOT_TOKEN).build()
        
        # ثبت handlers
        logger.info("📝 ثبت handlers...")
        
        # Start conversation
        start_handler = get_start_conversation_handler()
        app.add_handler(start_handler)
        logger.info("  ✓ Start handler")
        
        # دستورات
        app.add_handler(CommandHandler('menu', menu_command))
        app.add_handler(CommandHandler('help', help_command))
        app.add_handler(CommandHandler('status', status_command))
        logger.info("  ✓ Command handlers")
        
        # Settings handlers
        for handler in get_settings_handlers():
            app.add_handler(handler)
        logger.info("  ✓ Settings handlers")
        
        # Error handler
        app.add_error_handler(error_handler)
        logger.info("  ✓ Error handler")
        
        # Scheduler
        logger.info("⏰ راه‌اندازی Scheduler...")
        scheduler = setup_scheduler(app.job_queue)
        app.bot_data['scheduler'] = scheduler
        logger.info("✅ Scheduler OK")
        
        # Post init callback
        app.post_init = post_init
        
        # شروع
        logger.info("="*60)
        logger.info("✅ تمام تنظیمات کامل شد!")
        logger.info("📡 ربات در حال اجراست...")
        logger.info("⏹️ برای توقف: Ctrl+C")
        logger.info("="*60)
        
        # Run polling
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
        
    except KeyboardInterrupt:
        logger.info("\n⛔ ربات متوقف شد (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"❌ خطای کلی: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 خداحافظ!")


if __name__ == '__main__':
    main()