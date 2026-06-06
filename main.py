#!/usr/bin/env python3
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
from bot.handlers.search import get_search_conversation_handler
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


async def health_check(request):
    return web.Response(text="Bot is running!", status=200)


async def start_health_server():
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
    logger.error("❌ خطا رخ داد!", exc_info=context.error)
    if isinstance(context.error, (TimedOut, NetworkError)):
        logger.warning("⚠️ Network issue - ربات ادامه میده...")
        return
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ متأسفانه یه مشکلی پیش اومد!\nلطفاً دوباره امتحان کن یا /start بزن."
            )
    except Exception as e:
        logger.error(f"خطا در ارسال پیام خطا: {e}")


async def menu_command(update: Update, context):
    from bot.handlers.settings import show_menu
    await show_menu(update, context)


async def help_command(update: Update, context):
    help_text = """
🎵 <b>راهنمای ربات موزیک روزانه</b>

📋 <b>دستورات:</b>
/start - شروع و تنظیمات
/menu - منوی اصلی
/search - جستجوی موزیک
/status - وضعیت فعلی
/help - این راهنما
    """
    await update.message.reply_text(help_text, parse_mode='HTML')


async def status_command(update: Update, context):
    from core.database import SessionLocal, UserSettings, UserGenre
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
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
        await update.message.reply_text(status_text, parse_mode='HTML')
    finally:
        db.close()


async def post_init(application: Application):
    logger.info("🤖 ربات آماده است!")


def create_application():
    return Application.builder() \
        .token(config.BOT_TOKEN) \
        .connect_timeout(30) \
        .read_timeout(30) \
        .write_timeout(30) \
        .pool_timeout(30) \
        .build()


async def main_async():
    logger.info("="*60)
    logger.info("🚀 شروع راه‌اندازی ربات موزیک...")
    logger.info("="*60)

    config.validate()
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN موجود نیست!")
        sys.exit(1)

    init_db()
    await start_health_server()

    app = create_application()

    logger.info("📝 ثبت handlers...")

    # ====== گروه -2: ConversationHandlers (اولویت بالاتر) ======
    app.add_handler(get_start_conversation_handler(), group=-2)
    logger.info("  ✓ Start conversation handler (group -2)")

    app.add_handler(get_search_conversation_handler(), group=-2)
    logger.info("  ✓ Search conversation handler (group -2)")

    # ====== گروه -1: دستورات command ======
    app.add_handler(CommandHandler('menu', menu_command), group=-1)
    app.add_handler(CommandHandler('help', help_command), group=-1)
    app.add_handler(CommandHandler('status', status_command), group=-1)
    logger.info("  ✓ Command handlers (group -1)")

    # ====== گروه 0: منوی اصلی Reply keyboard - باید قبل از settings باشه ======
    for handler in get_main_menu_handlers():
        app.add_handler(handler, group=0)
    logger.info("  ✓ Main menu handlers (group 0)")

    # ====== گروه 1: Settings (inline callbacks + custom time text) ======
    for handler in get_settings_handlers():
        app.add_handler(handler, group=1)
    logger.info("  ✓ Settings handlers (group 1)")

    # ====== گروه 2: پردازش ورودی (voice/video/text search) ======
    for handler in get_input_processor_handlers():
        app.add_handler(handler, group=2)
    logger.info("  ✓ Input processor handlers (group 2)")

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
    logger.info("="*60)

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
