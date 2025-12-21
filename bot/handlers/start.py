"""
Handler برای دستور /start و فرآیند Setup اولیه (به‌روزشده برای multi-genre)
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
    get_time_selection_keyboard,
    get_destination_keyboard,
    get_main_menu_keyboard,
    get_back_to_menu_button
)
from bot.handlers.genre import show_genre_selection  # استفاده از سیستم جدید ژانر
from bot.states import (
    SETTING_TIME,
    CHOOSING_DESTINATION,
    SETTING_CHANNEL
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start - خوش‌آمدگویی و شروع فرآیند تنظیمات"""
    user = update.effective_user
    
    # ثبت یا به‌روزرسانی کاربر (full_name رو حذف کردیم)
    get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    welcome_text = f"""
🎵 سلام {user.first_name} عزیز! خوش اومدی! 👋

به ربات موزیک روزانه من خوش اومدی 🎶

من هر روز برات یه آهنگ جدید و خفن میفرستم، دقیقاً طبق سلیقه‌ت!

برای شروع، اول بگو چه سبک موزیکی دوست داری؟

👇 چندتا ژانر که دوست داری رو انتخاب کن (می‌تونی چندتا بزنی!):
    """
    
    await update.message.reply_text(welcome_text)
    
    # مستقیم رفتن به انتخاب ژانر (با سیستم multi-select جدید)
    await show_genre_selection(update, context, edit=False)
    
    return SETTING_TIME  # حالا مستقیم می‌ریم مرحله بعدی (زمان) بعد از تأیید ژانر در genre.py


# ==================== Time Selection ====================

async def time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربر زمان رو از کیبورد انتخاب کرده"""
    query = update.callback_query
    await query.answer()
    
    time = query.data.replace('time_', '')
    
    # ذخیره زمان در دیتابیس
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == query.from_user.id
        ).first()
        
        if settings:
            settings.send_time = time
            db.commit()
    finally:
        db.close()
    
    await query.edit_message_text(
        text=f"✅ زمان ارسال روزانه تنظیم شد: {time}\n\n"
             "حالا کجا آهنگ‌ها رو بفرستم؟\n\n"
             "💬 به همین چت (پیوی)\n"
             "📢 یا به کانال؟",
        reply_markup=get_destination_keyboard()
    )
    
    return CHOOSING_DESTINATION


async def custom_time_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربر زمان رو دستی فرستاده (HH:MM)"""
    time = update.message.text.strip()
    
    from utils.helpers import validate_time_format  # فرض می‌کنیم این تابع داری
    
    if not validate_time_format(time):
        await update.message.reply_text(
            "❌ فرمت زمان اشتباهه! مثل 09:30 بفرست.\n\n"
            "یا از دکمه‌ها انتخاب کن.",
            reply_markup=get_time_selection_keyboard()
        )
        return SETTING_TIME
    
    # ذخیره در دیتابیس
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == update.effective_user.id
        ).first()
        
        if settings:
            settings.send_time = time
            db.commit()
    finally:
        db.close()
    
    await update.message.reply_text(
        f"✅ زمان {time} ذخیره شد!\n\n"
        "حالا مقصد رو انتخاب کن:",
        reply_markup=get_destination_keyboard()
    )
    
    return CHOOSING_DESTINATION


# ==================== Destination Selection ====================

async def destination_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربر مقصد ارسال رو انتخاب کرده"""
    query = update.callback_query
    await query.answer()
    
    dest = query.data.replace('dest_', '')
    
    # ذخیره در دیتابیس
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == query.from_user.id
        ).first()
        
        if settings:
            settings.send_to = dest
            if dest == 'private':
                settings.channel_id = None
            db.commit()
    finally:
        db.close()
    
    if dest == 'channel':
        await query.edit_message_text(
            text="کانال رو بفرست:\n\n"
                 "مثال: @my_channel یا -1001234567890\n\n"
                 "من باید ادمین باشم!",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_CHANNEL
    else:
        await query.edit_message_text(
            text="تمام! تنظیماتت کامل شد 🎉\n\n"
                 "از فردا هر روز موزیک برات میاد!\n"
                 "هر وقت خواستی با /menu تنظیمات رو تغییر بده.",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END


async def channel_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.handlers.channel import receive_channel_id  # برای جلوگیری از circular import
    return await receive_channel_id(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد. با /start دوباره شروع کن.")
    return ConversationHandler.END


# ==================== Conversation Handler ====================

def get_start_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            SETTING_TIME: [
                CallbackQueryHandler(time_selected, pattern=r'^time_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_time_received)
            ],
            CHOOSING_DESTINATION: [
                CallbackQueryHandler(destination_selected, pattern=r'^dest_')
            ],
            SETTING_CHANNEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, channel_received)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True,
        per_chat=False
    )