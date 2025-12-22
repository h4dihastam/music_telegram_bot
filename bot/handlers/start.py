"""
Handler برای دستور /start و فرآیند Setup اولیه
"""
import re
from telegram import Update
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.error import TelegramError, BadRequest, Forbidden

from core.database import get_or_create_user, SessionLocal, UserSettings
from bot.keyboards.inline import (
    get_main_menu_keyboard,
    get_time_selection_keyboard,
    get_destination_keyboard,
    get_back_to_menu_button
)
from bot.handlers.genre import show_genre_selection, handle_genre_selection
from bot.states import CHOOSING_GENRE, SETTING_TIME, CHOOSING_DESTINATION, SETTING_CHANNEL


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.effective_user
    
    get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    welcome_text = f"""
🎵 سلام {user.first_name} عزیز! خوش اومدی! 👋

به ربات موزیک روزانه خوش اومدی 🎶

من هر روز برات یه آهنگ جدید میفرستم طبق سلیقه‌ت!

بیا شروع کنیم! اول ژانر مورد علاقه‌ات رو انتخاب کن 👇
    """
    
    if update.message:
        await update.message.reply_text(welcome_text)
    
    await show_genre_selection(update, context, edit=False)
    return CHOOSING_GENRE


async def time_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب زمان"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("time_"):
        if data == "time_custom":
            await query.edit_message_text(
                text="⏰ زمان دلخواه رو به فرمت HH:MM بفرست (مثل 09:30):"
            )
            return SETTING_TIME
        
        send_time = data.split("_")[1]
        user_id = update.effective_user.id
        
        db = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if settings:
                settings.send_time = send_time
                db.commit()
                
                # تنظیم scheduler
                scheduler = context.bot_data.get('scheduler')
                if scheduler:
                    from core.scheduler import schedule_user_daily_music_helper
                    schedule_user_daily_music_helper(user_id, scheduler)
        finally:
            db.close()
        
        await query.edit_message_text(
            text=f"✅ زمان ارسال به {send_time} تنظیم شد!\n\n"
                 "حالا کجا بفرستم؟",
            reply_markup=get_destination_keyboard()
        )
        return CHOOSING_DESTINATION


async def custom_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت زمان سفارشی"""
    from utils.helpers import validate_time_format
    
    time_str = update.message.text.strip()
    
    if not validate_time_format(time_str):
        await update.message.reply_text("❌ فرمت اشتباه! HH:MM وارد کن (مثل 09:30)")
        return SETTING_TIME
    
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings:
            settings.send_time = time_str
            db.commit()
            
            # تنظیم scheduler
            scheduler = context.bot_data.get('scheduler')
            if scheduler:
                from core.scheduler import schedule_user_daily_music_helper
                schedule_user_daily_music_helper(user_id, scheduler)
    finally:
        db.close()
    
    await update.message.reply_text(
        text=f"✅ زمان ارسال به {time_str} تنظیم شد!\n\n"
             "حالا کجا بفرستم؟",
        reply_markup=get_destination_keyboard()
    )
    return CHOOSING_DESTINATION


async def destination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب مقصد"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings:
            await query.edit_message_text("❌ تنظیمات پیدا نشد!")
            return ConversationHandler.END
        
        if data == "dest_private":
            settings.send_to = "private"
            settings.channel_id = None
            db.commit()
            
            # تنظیم scheduler
            scheduler = context.bot_data.get('scheduler')
            if scheduler:
                from core.scheduler import schedule_user_daily_music_helper
                schedule_user_daily_music_helper(user_id, scheduler)
            
            await query.edit_message_text(
                text="✅ تنظیمات با موفقیت ذخیره شد!\n\n"
                     "🎵 هر روز یه آهنگ جدید میگیری!\n\n"
                     "از /menu می‌تونی تنظیمات رو تغییر بدی 👇",
                reply_markup=get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        elif data == "dest_channel":
            await query.edit_message_text(
                text="📢 خوبه! حالا آیدی کانال رو برام بفرست:\n\n"
                     "مثال:\n"
                     "• @my_music_channel\n"
                     "• -1001234567890\n\n"
                     "⚠️ مهم: من باید **ادمین** کانال باشم!",
                reply_markup=None
            )
            return SETTING_CHANNEL
    finally:
        db.close()


async def channel_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آیدی کانال"""
    channel_input = update.message.text.strip()
    user_id = update.effective_user.id
    
    try:
        if channel_input.startswith('@'):
            chat_id = channel_input
        else:
            chat_id = int(channel_input)

        chat = await context.bot.get_chat(chat_id)

        admins = await context.bot.get_chat_administrators(chat_id)
        bot_is_admin = any(admin.user.id == context.bot.id for admin in admins)

        if not bot_is_admin:
            await update.message.reply_text(
                "⚠️ من ادمین کانال نیستم!\n\n"
                "لطفاً من رو ادمین کن و دوباره امتحان کن.",
                reply_markup=get_back_to_menu_button()
            )
            return SETTING_CHANNEL

        display_id = f"@{chat.username}" if chat.username else str(chat_id)

        db = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if settings:
                settings.send_to = "channel"
                settings.channel_id = str(chat_id)
                db.commit()
                
                # تنظیم scheduler
                scheduler = context.bot_data.get('scheduler')
                if scheduler:
                    from core.scheduler import schedule_user_daily_music_helper
                    schedule_user_daily_music_helper(user_id, scheduler)
        finally:
            db.close()

        await update.message.reply_text(
            f"✅ عالی! کانال تنظیم شد:\n\n"
            f"📢 {chat.title if hasattr(chat, 'title') else display_id}\n\n"
            f"تنظیمات کامل شد. /menu برای منو.",
            reply_markup=get_main_menu_keyboard()
        )

        return ConversationHandler.END

    except (BadRequest, Forbidden, ValueError, TelegramError) as e:
        await update.message.reply_text(
            f"❌ خطا: آیدی کانال رو درست وارد کن!\n\n"
            "مطمئن شو من ادمینم.",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_CHANNEL


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو conversation"""
    await update.message.reply_text(
        "❌ لغو شد! برای شروع دوباره /start بزن.",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


def get_start_conversation_handler():
    """ساخت conversation handler"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('start', start_command)
        ],
        states={
            CHOOSING_GENRE: [
                CallbackQueryHandler(
                    handle_genre_selection,
                    pattern=r'^(genre_select_|genre_confirm)'
                )
            ],
            SETTING_TIME: [
                CallbackQueryHandler(
                    time_selection_handler, 
                    pattern=r'^time_'
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    custom_time_handler
                )
            ],
            CHOOSING_DESTINATION: [
                CallbackQueryHandler(
                    destination_handler, 
                    pattern=r'^dest_'
                )
            ],
            SETTING_CHANNEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    channel_id_handler
                )
            ],
        },
        fallbacks=[
            CommandHandler('start', start_command),
            CommandHandler('cancel', cancel_handler),
        ],
        per_user=True,
        per_chat=False,
        allow_reentry=True,
        name="start_conversation"
    )