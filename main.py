#!/usr/bin/env python3
"""
ربات موزیک تلگرام - با قابلیت جستجو و موزیک فارسی
نسخه 2.0
"""
import logging
import sys
import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler
from telegram.error import TimedOut, NetworkError
from aiohttp import web

from core.config import config
from core.database import init_db
from core.scheduler import setup_scheduler, schedule_all_active_users
from bot.handlers import get_start_conversation_handler, get_settings_handlers
from bot.handlers.search import get_search_conversation_handler  # ✅ اضافه شد
from bot.handlers.main_menu import get_main_menu_handlers
from bot.handlers.input_processor import get_input_processor_handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8') if os.path.exists('/app') else logging.StreamHandler()
    ]
)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ✅ Health Check Server
async def health_check(request):
    """Endpoint برای health check"""
    return web.Response(text="Bot is running!", status=200)


async def start_health_server():
    """راه‌اندازی HTTP server برای health check"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    port = int(os.getenv('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Health server running on port {port}")


async def error_handler(update: Update, context):
    """مدیریت خطاها"""
    logger.error("❌ خطا رخ داد!", exc_info=context.error)
    
    # اگه timeout یا network error بود، نادیده بگیر
    if isinstance(context.error, (TimedOut, NetworkError)):
        logger.warning("⚠️ Network issue - ربات ادامه میده...")
        return
    
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
/search - جستجوی موزیک 🔍
/status - وضعیت فعلی
/help - این راهنما

🎯 <b>قابلیت‌ها:</b>
✅ انتخاب ژانر موسیقی (فارسی و خارجی)
✅ ارسال خودکار روزانه
✅ ارسال به پیوی یا کانال
✅ دریافت متن آهنگ
✅ دانلود MP3 کامل
✅ جستجوی دستی موزیک
✅ موزیک فارسی (پاپ، سنتی، رپ)

💡 <b>نکات:</b>
- هر روز در زمان انتخابی موزیک میگیری
- می‌تونی چند ژانر انتخاب کنی
- برای کانال، ربات باید ادمین باشه
- با /search می‌تونی هر آهنگی رو جستجو کنی
- موزیک فارسی کامل پشتیبانی میشه! 🇮🇷
    """
    await update.message.reply_text(
        help_text,
        parse_mode='HTML'
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
        
        if not settings:
            await update.message.reply_text("❌ تنظیماتی یافت نشد. /start را بزنید.")
            return

        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        genre_list = ", ".join([g.genre for g in genres]) if genres else "انتخاب نشده"
        
        status_text = (
            f"📊 <b>وضعیت ربات شما:</b>\n\n"
            f"⏰ زمان ارسال: {settings.send_time}\n"
            f"🎵 ژانرها: {genre_list}\n"
            f"📍 مقصد: {settings.send_to}\n"
            f"🌍 منطقه زمانی: {settings.timezone}\n"
            f"🔄 ارسال خودکار: {'✅ فعال' if settings.auto_send_enabled else '❌ غیرفعال'}"
        )
        
        if settings.send_to == 'channel' and settings.channel_id:
            status_text += f"\n📢 کانال: {settings.channel_id}"
        
        await update.message.reply_text(status_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Status error: {e}", exc_info=True)
        await update.message.reply_text("خطایی در دریافت وضعیت رخ داد.")
    finally:
        db.close()


async def post_init(application: Application):
    """بعد از راه‌اندازی"""
    logger.info("🤖 ربات آماده است!")
    logger.info(f"👤 Bot Username: @{application.bot.username}")


def create_application():
    """ساخت Application با تنظیمات بهتر"""
    return Application.builder() \
        .token(config.BOT_TOKEN) \
        .connect_timeout(30) \
        .read_timeout(30) \
        .write_timeout(30) \
        .pool_timeout(30) \
        .build()


async def main_async():
    """Main async function - اجرای ربات"""
    logger.info("="*60)
    logger.info("🚀 شروع راه‌اندازی ربات موزیک...")
    logger.info("="*60)
    
    logger.info("⚙️ بررسی تنظیمات...")
    config.validate()
    
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN موجود نیست!")
        sys.exit(1)
    
    logger.info("✅ تنظیمات OK")
    
    logger.info("🗄️ راه‌اندازی دیتابیس...")
    init_db()
    logger.info("✅ دیتابیس OK")
    
    # شروع health server
    await start_health_server()
    
    logger.info("🤖 ساخت Application...")
    app = create_application()
    
    logger.info("📝 ثبت handlers...")
    
    # Start handler
    start_handler = get_start_conversation_handler()
    app.add_handler(start_handler)
    logger.info("  ✓ Start handler")
    
    # ✅ Search handler - جدید! 🔍
    search_handler = get_search_conversation_handler()
    app.add_handler(search_handler)
    logger.info("  ✓ Search handler")
    
    # Command handlers
    app.add_handler(CommandHandler('menu', menu_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('status', status_command))
    logger.info("  ✓ Command handlers")
    
    # Settings handlers
    for handler in get_settings_handlers():
        app.add_handler(handler)
    logger.info("  ✓ Settings handlers")

    # Reply menu handlers
    for handler in get_main_menu_handlers():
        app.add_handler(handler, group=0)
    logger.info("  ✓ Main menu handlers")

    # Voice/audio/video/link/name processors run after menu routing
    for handler in get_input_processor_handlers():
        app.add_handler(handler, group=1)
    logger.info("  ✓ Input processor handlers")
    
    app.add_error_handler(error_handler)
    logger.info("  ✓ Error handler")
    
    logger.info("⏰ راه‌اندازی Scheduler...")
    scheduler = setup_scheduler(app.job_queue)
    app.bot_data['scheduler'] = scheduler
    schedule_all_active_users(scheduler)
    logger.info("✅ Scheduler OK")
    
    app.post_init = post_init
    
    logger.info("="*60)
    logger.info("✅ تمام تنظیمات کامل شد!")
    logger.info("🎵 نسخه 2.0 - با موزیک فارسی و جستجو")
    logger.info("="*60)
    
    # اجرای bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    
    logger.info("🤖 Bot is running. Press Ctrl+C to stop.")
    
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n⛔ دریافت سیگنال توقف...")
    finally:
        logger.info("🛑 Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main():
    """نقطه ورود اصلی"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\n⛔ ربات متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطای fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 خداحافظ!")


if __name__ == '__main__':
    main()