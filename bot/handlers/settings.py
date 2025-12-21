"""
Handler برای تنظیمات و منوی اصلی
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from core.database import SessionLocal, User, UserSettings, UserGenre
from bot.keyboards.inline import (
    get_main_menu_keyboard,
    get_genres_keyboard,
    get_time_selection_keyboard,
    get_destination_keyboard
)


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            text="🎵 منوی اصلی\n\nیکی از گزینه‌ها رو انتخاب کن:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            text="🎵 منوی اصلی\n\nیکی از گزینه‌ها رو انتخاب کن:",
            reply_markup=get_main_menu_keyboard()
        )


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت فعلی کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # دریافت اطلاعات از دیتابیس
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        genres = db.query(UserGenre).filter(
            UserGenre.user_id == user_id
        ).all()
        
        if not settings:
            await query.edit_message_text(
                text="❌ هنوز تنظیماتی ثبت نکردی!\n\n"
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
        """
        
        from bot.keyboards.inline import get_back_button
        await query.edit_message_text(
            text=status_text.strip(),
            reply_markup=get_back_button()
        )
        
    finally:
        db.close()


async def change_genre_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تغییر ژانر"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="🎵 ژانر جدید رو انتخاب کن:",
        reply_markup=get_genres_keyboard()
    )


async def change_time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تغییر زمان"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="⏰ زمان جدید رو انتخاب کن:",
        reply_markup=get_time_selection_keyboard()
    )


async def change_destination_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تغییر مقصد"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="📍 مقصد جدید رو انتخاب کن:",
        reply_markup=get_destination_keyboard()
    )


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک‌های منو"""
    query = update.callback_query
    data = query.data
    
    if data == "menu_back":
        await show_menu(update, context)
    elif data == "menu_status":
        await show_status(update, context)
    elif data == "menu_change_genre":
        await change_genre_menu(update, context)
    elif data == "menu_change_time":
        await change_time_menu(update, context)
    elif data == "menu_change_dest":
        await change_destination_menu(update, context)
    elif data == "menu_random":
        await send_random_music(update, context)


async def send_random_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال یک موزیک تصادفی الان"""
    query = update.callback_query
    await query.answer("🎲 در حال جستجوی یک آهنگ تصادفی...", show_alert=False)
    
    user_id = update.effective_user.id
    
    # گرفتن ژانر کاربر
    from core.database import UserGenre
    db = SessionLocal()
    try:
        user_genres = db.query(UserGenre).filter(
            UserGenre.user_id == user_id
        ).all()
        
        if not user_genres:
            await query.edit_message_text(
                text="❌ هنوز ژانر موسیقی انتخاب نکردی!\n\n"
                     "از /start استفاده کن.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        genre = user_genres[0].genre
        
    finally:
        db.close()
    
    # ارسال پیام انتظار
    await query.edit_message_text(
        text="🎵 در حال پیدا کردن یه آهنگ خفن برات...\n\n"
             "⏳ لطفاً چند لحظه صبر کن..."
    )
    
    # ارسال موزیک
    from services.music_sender import send_music_to_user
    success = await send_music_to_user(
        bot=context.bot,
        user_id=user_id,
        genre=genre,
        send_to='private',
        download_file=True
    )
    
    if success:
        await query.edit_message_text(
            text="✅ آهنگ ارسال شد! 🎉\n\n"
                 "امیدوارم خوشت بیاد! 🎵",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            text="❌ متأسفانه نتونستم آهنگ پیدا کنم!\n\n"
                 "لطفاً بعداً دوباره امتحان کن.",
            reply_markup=get_main_menu_keyboard()
        )


# ==================== Handler Registration ====================

def get_settings_handlers():
    """لیست تمام handler های مربوط به تنظیمات"""
    return [
        CallbackQueryHandler(menu_callback_handler, pattern=r'^menu_'),
    ]