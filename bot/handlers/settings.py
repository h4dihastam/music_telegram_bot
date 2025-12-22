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
from bot.handlers.genre import show_genre_selection, handle_genre_selection  # برای تغییر ژانر
from bot.handlers.channel import get_channel_handlers  # اگر نیاز باشه
import random

# ایمپورت برای scheduler (برای اضافه کردن job بعد از ذخیره تنظیمات)
from core.scheduler import schedule_user_daily_music

logger = logging.getLogger(__name__)


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
        
        channel = settings.channel_id if settings.send_to == 'channel' else "پیوی (خصوصی)"
        
        status_text = f"ℹ️ وضعیت فعلی تو:\n\n"
        status_text += f"🎵 ژانرها: {genre_list}\n"
        status_text += f"⏰ زمان ارسال: {settings.send_time}\n"
        status_text += f"📍 مقصد: {channel}\n"
        status_text += f"🕒 منطقه زمانی: {settings.timezone}\n\n"
        status_text += "برای تغییر، از منو استفاده کن!"
        
        await query.edit_message_text(
            text=status_text,
            reply_markup=get_main_menu_keyboard()
        )
    finally:
        db.close()


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های منو"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "menu_change_genre":
        await show_genre_selection(update, context)
        
    elif data == "menu_change_time":
        await query.edit_message_text(
            text="⏰ زمان ارسال روزانه رو انتخاب کن:",
            reply_markup=get_time_selection_keyboard()
        )
        
    elif data == "menu_change_dest":
        await query.edit_message_text(
            text="📍 کجا موزیک‌ها رو بفرستم؟",
            reply_markup=get_destination_keyboard()
        )
        
    elif data == "menu_status":
        await show_status(update, context)
        
    elif data == "menu_random":
        await send_random_music(update, context)
    
    elif data == "menu_back":
        await show_menu(update, context)


# handler برای تغییر زمان (مثال - بسته به کد کاملت)
async def change_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... کد تغییر زمان (فرض کنیم زمان ذخیره می‌شه)
    
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        # ذخیره زمان جدید
        # settings.send_time = new_time
        db.commit()
        
        # اضافه کردن/بروزرسانی job روزانه
        schedule_user_daily_music(user_id)
    finally:
        db.close()


# handler برای تغییر مقصد (مثال)
async def change_dest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... کد تغییر مقصد
    
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        # ذخیره مقصد جدید
        # settings.send_to = new_dest
        db.commit()
        
        # اضافه کردن/بروزرسانی job روزانه
        schedule_user_daily_music(user_id)
    finally:
        db.close()


async def send_random_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال موزیک تصادفی حالا"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
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
        
        genre = random.choice([g.genre for g in user_genres])
        
    finally:
        db.close()
    
    await query.edit_message_text(
        text="🎵 در حال پیدا کردن یه آهنگ خفن برات...\n\n"
             "⏳ لطفاً چند لحظه صبر کن..."
    )
    
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
        # اگر handler جدا برای change_time یا change_dest داری، اضافه کن
        # CallbackQueryHandler(change_time_handler, pattern=r'^time_'),
        # CallbackQueryHandler(change_dest_handler, pattern=r'^dest_'),
    ]