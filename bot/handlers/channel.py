"""
Handler برای مدیریت تنظیمات کانال
- انتخاب ارسال به کانال
- دریافت و اعتبارسنجی آیدی کانال
- چک کردن دسترسی ادمین ربات
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import TelegramError, Forbidden, BadRequest

from core.database import SessionLocal, UserSettings
from bot.keyboards.inline import get_back_to_menu_button
from bot.states import SETTING_CHANNEL

# اضافه برای scheduler
from core.scheduler import schedule_user_daily_music


async def choose_channel_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربر گزینه 'ارسال به کانال' رو انتخاب کرده"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # ذخیره موقت انتخاب مقصد
    context.user_data['pending_destination'] = 'channel'

    await query.edit_message_text(
        text="📢 خوبه! حالا آیدی کانال رو برام بفرست:\n\n"
             "مثال:\n"
             "• @my_music_channel\n"
             "• -1001234567890\n\n"
             "⚠️ مهم: من باید **ادمین** کانال باشم تا بتونم موزیک بفرستم!",
        reply_markup=get_back_to_menu_button()
    )

    return SETTING_CHANNEL


async def receive_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت و پردازش آیدی کانال از کاربر"""
    if update.callback_query:
        await update.callback_query.answer()
        return

    user_id = update.effective_user.id
    channel_input = update.message.text.strip()

    try:
        # تبدیل به chat_id
        if channel_input.startswith('@'):
            chat_id = channel_input
        else:
            chat_id = int(channel_input)

        # چک کردن کانال
        chat = await context.bot.get_chat(chat_id)

        # چک ادمین بودن ربات
        admins = await context.bot.get_chat_administrators(chat_id)
        bot_is_admin = any(admin.user.id == context.bot.id for admin in admins)

        if not bot_is_admin:
            await update.message.reply_text(
                "⚠️ من ادمین کانال نیستم! اول منو ادمین کن بعد دوباره امتحان کن.",
                reply_markup=get_back_to_menu_button()
            )
            return SETTING_CHANNEL

        display_id = f"@{chat.username}" if chat.username else str(chat_id)

        # ذخیره تنظیمات
        db = SessionLocal()
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings:
            await update.message.reply_text("❌ اول باید تنظیمات اولیه رو انجام بدی (/start)")
            return ConversationHandler.END

        settings.send_to = "channel"
        settings.channel_id = str(chat_id)
        db.commit()

        # اضافه کردن/بروزرسانی job روزانه بعد از ذخیره
        schedule_user_daily_music(user_id)
    finally:
        db.close()

    # پیام تأیید نهایی
    await update.message.reply_text(
        f"✅ عالی! کانال با موفقیت تنظیم شد:\n\n"
        f"📢 {chat.title if hasattr(chat, 'title') else display_id}\n"
        f"🆔 {display_id}\n\n"
        f"از فردا هر روز موزیک تو این کانال میاد! 🎵",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به منو", callback_data="menu_back")]
        ])
    )

    # پاک کردن داده موقت
    if 'pending_destination' in context.user_data:
        del context.user_data['pending_destination']

    return ConversationHandler.END


# ==================== Handler Registration ====================

def get_channel_handlers():
    """ثبت هندلرهای مربوط به کانال"""
    return [
        CallbackQueryHandler(choose_channel_destination, pattern=r'^dest_channel$'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel_id),
    ]