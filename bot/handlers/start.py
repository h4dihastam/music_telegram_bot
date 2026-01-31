"""
Handler /start - نسخه مدرن با UX حرفه‌ای
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
from bot.keyboards.reply import get_main_menu_reply_keyboard
from bot.keyboards.inline import (
    get_time_selection_keyboard,
    get_destination_keyboard,
    get_back_to_menu_button
)
from bot.handlers.genre import show_genre_selection, handle_genre_selection
from bot.states import CHOOSING_GENRE, SETTING_TIME, CHOOSING_DESTINATION, SETTING_CHANNEL


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    دستور /start - پیام خوش‌آمدگویی زیبا
    """
    user = update.effective_user
    
    # ساخت/بروزرسانی کاربر
    get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # چک کنیم که آیا تنظیمات اولیه انجام شده؟
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()
        
        has_setup = settings is not None
    finally:
        db.close()
    
    # پیام خوش‌آمدگویی با emoji های زیاد
    if has_setup:
        # کاربر قبلاً setup کرده
        welcome_text = f"""
🎵 <b>سلام {user.first_name} عزیز! خوش برگشتی!</b> 👋

ربات موزیک <b>RitmLine</b> آماده است! 🎶

<i>از منوی زیر می‌تونی استفاده کنی:</i>

🔍 <b>جستجوی سریع</b> - هر آهنگی که بخوای!
🎲 <b>پخش زنده</b> - موزیک تصادفی الان
❤️ <b>لایک‌ها</b> - آهنگ‌های محبوبت
📥 <b>دانلودها</b> - تاریخچه دانلودت

✨ <i>بزن بریم!</i>
        """
    else:
        # کاربر جدید
        welcome_text = f"""
🎵 <b>سلام {user.first_name} عزیز! به ربات RitmLine خوش اومدی!</b> 🎉

من هر روز برات یه آهنگ جدید میفرستم 🎶

<b>✨ قابلیت‌های من:</b>

🔍 جستجوی هوشمند موزیک
🎤 تشخیص آهنگ از ویس
📱 دانلود از لینک اینستاگرام
❤️ لایک و ذخیره آهنگ
📜 نمایش متن آهنگ
⏰ ارسال خودکار روزانه
🇮🇷 آهنگ‌های ایرانی کامل

<i>بیا شروع کنیم! اول ژانر مورد علاقه‌ات رو انتخاب کن 👇</i>
        """
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=get_main_menu_reply_keyboard() if has_setup else None
        )
    
    if not has_setup:
        # نمایش انتخاب ژانر برای کاربران جدید
        await show_genre_selection(update, context, edit=False)
        return CHOOSING_GENRE
    
    return ConversationHandler.END


async def time_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب زمان"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("time_"):
        if data == "time_custom":
            await query.edit_message_text(
                text="⏰ زمان دلخواه رو به فرمت HH:MM بفرست\n\n"
                     "مثال: 09:30, 14:00, 21:45",
                reply_markup=get_back_to_menu_button()
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
        await update.message.reply_text(
            "❌ فرمت زمان اشتباه است!\n\n"
            "لطفاً به فرمت HH:MM وارد کنید (مثل 09:30)",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_TIME
    
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings:
            settings.send_time = time_str
            db.commit()
            
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
            
            scheduler = context.bot_data.get('scheduler')
            if scheduler:
                from core.scheduler import schedule_user_daily_music_helper
                schedule_user_daily_music_helper(user_id, scheduler)
            
            await query.edit_message_text(
                text="✅ <b>تمام! همه چیز آماده است!</b> 🎉\n\n"
                     "🎵 از امروز هر روز یه آهنگ جدید دریافت می‌کنی!\n\n"
                     "<i>از منوی پایین می‌تونی استفاده کنی:</i>",
                parse_mode='HTML'
            )
            
            # ارسال منوی اصلی
            await context.bot.send_message(
                chat_id=user_id,
                text="🎵 منوی اصلی:",
                reply_markup=get_main_menu_reply_keyboard()
            )
            
            return ConversationHandler.END
        
        elif data == "dest_channel":
            await query.edit_message_text(
                text="📢 خوبه! حالا آیدی کانال رو برام بفرست:\n\n"
                     "مثال:\n"
                     "• @my_music_channel\n"
                     "• -1001234567890\n\n"
                     "⚠️ مهم: من باید **ادمین** کانال باشم!",
                reply_markup=get_back_to_menu_button()
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
                
                scheduler = context.bot_data.get('scheduler')
                if scheduler:
                    from core.scheduler import schedule_user_daily_music_helper
                    schedule_user_daily_music_helper(user_id, scheduler)
        finally:
            db.close()

        await update.message.reply_text(
            f"✅ <b>عالی! همه چیز آماده!</b> 🎉\n\n"
            f"📢 کانال: {chat.title if hasattr(chat, 'title') else display_id}\n\n"
            f"از امروز هر روز موزیک تو کانال میاد!",
            parse_mode='HTML',
            reply_markup=get_main_menu_reply_keyboard()
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
        "❌ لغو شد!",
        reply_markup=get_main_menu_reply_keyboard()
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
                ),
                CallbackQueryHandler(
                    lambda u, c: show_genre_selection(u, c),
                    pattern=r'^menu_back$'
                )
            ],
        },
        fallbacks=[
            CommandHandler('start', start_command),
            CommandHandler('cancel', cancel_handler),
            CallbackQueryHandler(
                lambda u, c: ConversationHandler.END,
                pattern=r'^menu_back$'
            )
        ],
        per_user=True,
        per_chat=False,
        allow_reentry=True,
        name="start_conversation"
    )