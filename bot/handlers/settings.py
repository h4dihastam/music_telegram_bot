"""
Handler برای تنظیمات و منوی اصلی - FIXED
"""
import random
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from core.database import SessionLocal, UserSettings, UserGenre
from bot.keyboards.inline import (
    get_main_menu_keyboard,
    get_time_selection_keyboard,
    get_destination_keyboard,
    get_back_to_menu_button
)
from bot.handlers.genre import show_genre_selection
from bot.states import SETTING_TIME

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
    """نمایش وضعیت فعلی"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        
        if not settings:
            await query.edit_message_text(
                text="❌ هنوز تنظیماتی ثبت نکردی!\n\nاز /start استفاده کن."
            )
            return
        
        genre_list = ", ".join([g.genre for g in genres]) if genres else "انتخاب نشده"
        channel = settings.channel_id if settings.send_to == 'channel' else "پیوی (خصوصی)"
        
        status_text = f"ℹ️ وضعیت فعلی:\n\n"
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
        # ✅ ذخیره state برای بعد
        context.user_data['changing_time_from_menu'] = True
        
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


async def change_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر زمان - FIXED"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("time_"):
        if data == "time_custom":
            # ✅ درخواست زمان سفارشی
            await query.edit_message_text(
                text="⏰ زمان دلخواه رو به فرمت HH:MM بفرست\n\n"
                     "مثال: 09:30, 14:00, 21:45",
                reply_markup=get_back_to_menu_button()
            )
            # ذخیره که منتظر ورودی کاربر هستیم
            context.user_data['waiting_for_custom_time'] = True
            return
        
        # زمان‌های از پیش تعیین شده
        send_time = data.split("_")[1]
        
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
                
                await query.edit_message_text(
                    text=f"✅ زمان ارسال به {send_time} تغییر کرد!",
                    reply_markup=get_main_menu_keyboard()
                )
        finally:
            db.close()


async def custom_time_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت زمان سفارشی از کاربر - FIXED"""
    # چک کنیم که واقعاً منتظر زمان بودیم
    if not context.user_data.get('waiting_for_custom_time'):
        return
    
    from utils.helpers import validate_time_format
    
    time_str = update.message.text.strip()
    user_id = update.effective_user.id
    
    # اعتبارسنجی
    if not validate_time_format(time_str):
        await update.message.reply_text(
            "❌ فرمت زمان اشتباه است!\n\n"
            "لطفاً به فرمت HH:MM وارد کنید (مثل 09:30)",
            reply_markup=get_back_to_menu_button()
        )
        return
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings:
            # ✅ ذخیره زمان واقعی
            settings.send_time = time_str
            db.commit()
            
            # تنظیم scheduler
            scheduler = context.bot_data.get('scheduler')
            if scheduler:
                from core.scheduler import schedule_user_daily_music_helper
                schedule_user_daily_music_helper(user_id, scheduler)
            
            await update.message.reply_text(
                text=f"✅ زمان ارسال به {time_str} تغییر کرد!",
                reply_markup=get_main_menu_keyboard()
            )
            
            # پاک کردن flag
            context.user_data.pop('waiting_for_custom_time', None)
        else:
            await update.message.reply_text(
                "❌ تنظیمات پیدا نشد!",
                reply_markup=get_main_menu_keyboard()
            )
    finally:
        db.close()


async def change_dest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر مقصد"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data == "dest_private":
        db = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if settings:
                settings.send_to = "private"
                settings.channel_id = None
                db.commit()
                
                # تنظیم scheduler
                scheduler = context.bot_data.get('scheduler')
                if scheduler:
                    from core.scheduler import schedule_user_daily_music_helper
                    schedule_user_daily_music_helper(user_id, scheduler)
                
                await query.edit_message_text(
                    text="✅ مقصد به پیوی تغییر کرد!",
                    reply_markup=get_main_menu_keyboard()
                )
        finally:
            db.close()


async def send_random_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال موزیک تصادفی"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        
        if not genres:
            await query.edit_message_text(
                text="❌ هنوز ژانر موسیقی انتخاب نکردی!",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        genre = random.choice([g.genre for g in genres])
    finally:
        db.close()
    
    await query.edit_message_text(
        text="🎵 در حال پیدا کردن آهنگ...\n⏳ صبر کن..."
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
            text="✅ آهنگ ارسال شد! 🎉",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            text="❌ نتونستم آهنگ پیدا کنم!",
            reply_markup=get_main_menu_keyboard()
        )


def get_settings_handlers():
    """لیست handlers تنظیمات - FIXED"""
    return [
        # Callback handlers
        CallbackQueryHandler(menu_callback_handler, pattern=r'^menu_'),
        CallbackQueryHandler(change_time_handler, pattern=r'^time_'),
        CallbackQueryHandler(change_dest_handler, pattern=r'^dest_'),
        
        # ✅ Message handler برای زمان سفارشی
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            custom_time_input_handler
        ),
    ]