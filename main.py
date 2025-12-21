"""
Music Telegram Bot - Entry Point
ربات تلگرام ارسال موزیک روزانه
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

# Import های داخلی
from core.config import config
from core.database import init_db
from bot.handlers import (
    get_start_conversation_handler,
    get_settings_handlers,
)

# تنظیم Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== Commands ====================

async def help_command(update: Update, context):
    """دستور /help"""
    help_text = """
🎵 راهنمای استفاده از ربات

📋 دستورات:
/start - شروع کار و تنظیمات اولیه
/menu - نمایش منوی اصلی
/status - نمایش وضعیت فعلی
/help - نمایش این راهنما

🎯 قابلیت‌ها:
• انتخاب ژانر موزیک مورد علاقه
• تنظیم زمان ارسال روزانه
• ارسال به پیوی یا کانال
• دریافت لینک Spotify و متن آهنگ

💡 نکات:
• من هر روز یه آهنگ جدید برات میذارم
• می‌تونی هر وقت خواستی تنظیماتت رو تغییر بدی
• برای ارسال به کانال، من باید ادمین کانال باشم

❓ مشکلی پیش اومد؟
با سازنده ربات تماس بگیر: @YourUsername
    """
    await update.message.reply_text(help_text)


async def menu_command(update: Update, context):
    """دستور /menu"""
    from bot.keyboards.inline import get_main_menu_keyboard
    await update.message.reply_text(
        text="🎵 منوی اصلی\n\nیکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=get_main_menu_keyboard()
    )


async def status_command(update: Update, context):
    """دستور /status"""
    from core.database import SessionLocal, UserSettings, UserGenre
    
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        genres = db.query(UserGenre).filter(
            UserGenre.user_id == user_id
        ).all()
        
        if not settings:
            await update.message.reply_text(
                "❌ هنوز تنظیماتی ثبت نکردی!\n\n"
                "از /start استفاده کن تا شروع کنیم."
            )
            return
        
        genre_list = ", ".join([g.genre for g in genres]) if genres else "انتخاب نشده"
        
        status_text = f"""
📊 وضعیت فعلی شما:

🎵 ژانر(ها): {genre_list}
⏰ زمان ارسال: {settings.send_time}
📍 مقصد ارسال: {"کانال" if settings.send_to == "channel" else "پیوی"}
{"📢 کانال: " + settings.channel_id if settings.channel_id else ""}
🌍 منطقه زمانی: {settings.timezone}

✅ ربات فعال است و آماده ارسال موزیک!
        """
        
        await update.message.reply_text(status_text.strip())
        
    finally:
        db.close()


# ==================== Error Handler ====================

async def error_handler(update: object, context):
    """مدیریت خطاها"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # اگه update یک پیام تلگرام بود، به کاربر خبر بده
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ متأسفانه یه خطایی پیش اومد!\n\n"
            "لطفاً دوباره تلاش کن یا با پشتیبانی تماس بگیر."
        )


# ==================== Unknown Messages ====================

async def unknown_message(update: Update, context):
    """پیام‌های ناشناخته"""
    await update.message.reply_text(
        "🤔 متوجه نشدم چی گفتی!\n\n"
        "از /help برای دیدن راهنما استفاده کن."
    )


# ==================== Main Function ====================

def main():
    """تابع اصلی - راه‌اندازی ربات"""
    
    print("🚀 در حال راه‌اندازی ربات...")
    
    # ✅ اعتبارسنجی تنظیمات
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"خطا در تنظیمات: {e}")
        return
    
    # ✅ ساخت دیتابیس
    print("📊 در حال ساخت دیتابیس...")
    init_db()
    
    # ✅ ساخت Application
    print("🤖 در حال ساخت Application...")
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # ✅ ثبت Handlers
    print("📝 در حال ثبت Handlers...")
    
    # Conversation Handler برای /start
    application.add_handler(get_start_conversation_handler())
    
    # Command Handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Settings Handlers
    for handler in get_settings_handlers():
        application.add_handler(handler)
    
    # Unknown Messages Handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message)
    )
    
    # Error Handler
    application.add_error_handler(error_handler)
    
    # ✅ راه‌اندازی Scheduler (برای ارسال روزانه)
    print("⏰ در حال راه‌اندازی Scheduler...")
    from core.scheduler import setup_scheduler
    scheduler = setup_scheduler(application.bot)
    
    # ذخیره scheduler در application برای استفاده در handlers
    application.bot_data['scheduler'] = scheduler
    
    print("✅ ربات آماده است!")
    print("=" * 50)
    print("🎵 Music Telegram Bot is running...")
    print(f"📋 {len(scheduler.get_all_jobs_info())} job فعال")
    print("=" * 50)
    
    # ✅ شروع polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True  # نادیده گرفتن پیام‌های قدیمی
    )


# ==================== Run ====================

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⛔ ربات متوقف شد (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ خطای کلی: {e}")
        raise
  #  ///////////////////////////// channel managment ///////////////////////////////
from bot.handlers.channel import get_channel_handlers

# داخل main():
for handler in get_channel_handlers():
    application.add_handler(handler)
    #ژانر
    from bot.handlers.genre import get_genre_handlers

# داخل main()، کنار بقیه هندلرها:
for handler in get_genre_handlers():
    application.add_handler(handler)