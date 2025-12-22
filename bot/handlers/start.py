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

from core.database import get_or_create_user, SessionLocal, UserSettings
from bot.keyboards.inline import (
    get_main_menu_keyboard,
    get_time_selection_keyboard,
    get_destination_keyboard
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
    """مدیریت انتخاب زمان از دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("time_"):
        if data == "time_custom":
            await query.edit_message_text(
                text="⏰ زمان دلخواه رو به فرمت HH:MM بفرست\n\n"
                     "مثال: 09:00 یا 14:30",
                reply_markup=None
            )
            return SETTING_TIME
        else:
            # زمان از پیش تعریف شده
            time_str = data.replace("time_", "")
            context.user_data['selected_time'] = time_str
            
            # ذخیره در دیتابیس
            user_id = update.effective_user.id
            db = SessionLocal()
            try:
                settings = db.query(UserSettings).filter(
                    UserSettings.user_id == user_id
                ).first()
                if settings:
                    settings.send_time = time_str
                    db.commit()
            finally:
                db.close()
            
            await query.edit_message_text(
                text=f"✅ زمان ارسال: {time_str}\n\n"
                     "حالا مقصد ارسال رو انتخاب کن:",
                reply_markup=get_destination_keyboard()
            )
            return CHOOSING_DESTINATION


async def custom_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت زمان دستی از کاربر"""
    time_str = update.message.text.strip()
    
    # اعتبارسنجی فرمت
    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str):
        await update.message.reply_text(
            "❌ فرمت زمان اشتباهه!\n\n"
            "باید به صورت HH:MM باشه (مثل 09:00 یا 14:30)\n"
            "دوباره بفرست:"
        )
        return SETTING_TIME
    
    context.user_data['selected_time'] = time_str
    
    # ذخیره در دیتابیس
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        if settings:
            settings.send_time = time_str
            db.commit()
    finally:
        db.close()
    
    await update.message.reply_text(
        text=f"✅ زمان ارسال: {time_str}\n\n"
             "حالا مقصد ارسال رو انتخاب کن:",
        reply_markup=get_destination_keyboard()
    )
    return CHOOSING_DESTINATION


async def destination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب مقصد"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data == "dest_private":
        # ذخیره در دیتابیس
        db = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(
                UserSettings.user_id == user_id
            ).first()
            if settings:
                settings.send_to = "private"
                settings.channel_id = None
                db.commit()
                
                # به‌روزرسانی scheduler
                scheduler = context.bot_data.get('scheduler')
                if scheduler:
                    scheduler.add_user_job(user_id, settings.send_time, settings.timezone)
        finally:
            db.close()
        
        await query.edit_message_text(
            text="✅ تنظیمات با موفقیت ذخیره شد!\n\n"
                 "🎵 هر روز یه آهنگ جدید میگیری!\n\n"
                 "از منو می‌تونی تنظیمات رو تغییر بدی 👇",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END
    
    elif data == "dest_channel":
        await query.edit_message_text(
            text="📢 خوبه! حالا آیدی کانال رو برام بفرست:\n\n"
                 "مثال:\n"
                 "• @my_music_channel\n"
                 "• -1001234567890\n\n"
                 "⚠️ مهم: من باید **ادمین** کانال باشم تا بتونم موزیک بفرستم!",
            reply_markup=None
        )
        return SETTING_CHANNEL


async def channel_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت و بررسی آیدی کانال"""
    from telegram.error import BadRequest, Forbidden, TelegramError
    
    channel_input = update.message.text.strip()
    user_id = update.effective_user.id
    bot = context.bot
    
    # اعتبارسنجی فرمت
    if not (channel_input.startswith('@') or (channel_input.startswith('-') and channel_input[1:].isdigit())):
        await update.message.reply_text(
            "❌ فرمت آیدی کانال اشتباهه!\n\n"
            "باید با @ شروع بشه یا آیدی عددی باشه (مثل -1001234567890)\n"
            "دوباره بفرست:"
        )
        return SETTING_CHANNEL
    
    try:
        if channel_input.startswith('@'):
            chat = await bot.get_chat(channel_input)
            chat_id = chat.id
        else:
            chat_id = int(channel_input)
            chat = await bot.get_chat(chat_id)
        
        # چک کردن ادمین بودن ربات
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ('administrator', 'creator'):
            await update.message.reply_text(
                "⚠️ من در این کانال ادمین نیستم!\n\n"
                "لطفاً من رو ادمین کن (با مجوز 'ارسال پیام') و دوباره آیدی رو بفرست."
            )
            return SETTING_CHANNEL
        
        # ذخیره در دیتابیس
        db = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(
                UserSettings.user_id == user_id
            ).first()
            if settings:
                settings.send_to = "channel"
                settings.channel_id = str(chat_id)
                db.commit()
                
                # به‌روزرسانی scheduler
                scheduler = context.bot_data.get('scheduler')
                if scheduler:
                    scheduler.add_user_job(user_id, settings.send_time, settings.timezone)
        finally:
            db.close()
        
        await update.message.reply_text(
            f"✅ عالی! کانال با موفقیت تنظیم شد:\n\n"
            f"📢 {chat.title if hasattr(chat, 'title') else channel_input}\n\n"
            f"از فردا هر روز موزیک تو این کانال میاد! 🎵",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END
        
    except (BadRequest, ValueError):
        await update.message.reply_text(
            "❌ کانال پیدا نشد! آیدی رو درست چک کن و دوباره بفرست."
        )
        return SETTING_CHANNEL
    except Forbidden:
        await update.message.reply_text(
            "🚫 من به این کانال دسترسی ندارم!\n\n"
            "لطفاً اول من رو به کانال اضافه کن و ادمین کن."
        )
        return SETTING_CHANNEL
    except TelegramError as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}\nدوباره تلاش کن.")
        return SETTING_CHANNEL


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو conversation"""
    await update.message.reply_text(
        "❌ لغو شد! برای شروع دوباره /start بزن.",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


def get_start_conversation_handler():
    """ساخت conversation handler برای /start"""
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