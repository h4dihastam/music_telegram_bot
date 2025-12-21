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
import random


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
        
        channel = settings.channel_id if settings.send_to == 'channel' else "پیوی"
        
        status_text = f"ℹ️ وضعیت فعلی تو:\n\n"
        status_text += f"🎵 ژانرها: {genre_list}\n"
        status_text += f"⏰ زمان ارسال: {settings.send_time}\n"
        status_text += f"📍 مقصد: {channel}\n"
        status_text += f"🌍 منطقه زمانی: {settings.timezone}\n\n"
        status_text += "هر چیزی خواستی تغییر بدی، از منو استفاده کن!"
        
        await query.edit_message_text(
            text=status_text,
            reply_markup=get_main_menu_keyboard()
        )
    finally:
        db.close()


async def change_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر ژانر"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # گرفتن ژانرهای فعلی
    db = SessionLocal()
    try:
        current_genres = [g.genre for g in db.query(UserGenre).filter(UserGenre.user_id == user_id).all()]
    finally:
        db.close()
    
    await query.edit_message_text(
        text="🎵 ژانرهای مورد علاقه‌ات رو انتخاب کن (چندتا هم می‌تونی بزنی!):",
        reply_markup=get_genres_keyboard(selected_genres=set(current_genres))
    )


async def change_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر زمان ارسال"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="⏰ زمان ارسال روزانه رو انتخاب کن\n\n"
             "یا دستی بفرست (HH:MM):",
        reply_markup=get_time_selection_keyboard()
    )


async def change_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر مقصد ارسال"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="📍 کجا آهنگ‌ها رو بفرستم؟",
        reply_markup=get_destination_keyboard()
    )


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کال‌بک‌های منو"""
    query = update.callback_query
    data = query.data
    
    if data == "menu_back":
        await show_menu(update, context)
        
    elif data == "menu_change_genre":
        await change_genre(update, context)
        
    elif data == "menu_change_time":
        await change_time(update, context)
        
    elif data == "menu_change_dest":
        await change_destination(update, context)
        
    elif data == "menu_status":
        await show_status(update, context)
        
    elif data == "menu_random":
        await show_random_music(update, context)


async def show_random_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال موزیک تصادفی (برای دکمه menu_random)"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # گرفتن ژانرهای کاربر
    db = SessionLocal()
    try:
        user_genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        
        if not user_genres:
            await query.edit_message_text(
                text="❌ هنوز ژانر موسیقی انتخاب نکردی!\n\n"
                     "از /start استفاده کن.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # انتخاب ژانر تصادفی اگر چندتا باشه
        genre = random.choice([g.genre for g in user_genres])
        
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