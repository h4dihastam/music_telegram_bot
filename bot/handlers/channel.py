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
from bot.states import SETTING_CHANNEL  # اگر state داری، یا می‌تونی بدون state استفاده کنی


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

    return SETTING_CHANNEL  # اگر از ConversationHandler استفاده می‌کنی


async def receive_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت و پردازش آیدی کانال از کاربر"""
    if update.callback_query:
        # اگر کاربر دکمه "برگشت" رو زده
        if update.callback_query.data == "back_to_menu":
            from bot.handlers.settings import show_menu
            return await show_menu(update, context)

    channel_input = update.message.text.strip()
    user_id = update.effective_user.id
    bot = context.bot

    # اعتبارسنجی اولیه فرمت
    if not (channel_input.startswith('@') or (channel_input.startswith('-') and channel_input[1:].isdigit())):
        await update.message.reply_text(
            "❌ فرمت آیدی کانال اشتباهه!\n\n"
            "باید با @ شروع بشه یا آیدی عددی باشه (مثل -1001234567890)\n"
            "دوباره بفرست:",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_CHANNEL

    # تلاش برای تبدیل به chat_id عددی
    try:
        if channel_input.startswith('@'):
            # تبدیل username به chat_id
            chat = await bot.get_chat(channel_input)
            chat_id = chat.id
            display_id = channel_input
        else:
            chat_id = int(channel_input)
            # گرفتن اطلاعات کانال برای نمایش بهتر
            chat = await bot.get_chat(chat_id)
            display_id = channel_input if len(channel_input) < 20 else f"{chat.title} ({channel_input})"

    except (BadRequest, ValueError):
        await update.message.reply_text(
            "❌ کانال پیدا نشد! آیدی رو درست چک کن و دوباره بفرست.",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_CHANNEL
    except Forbidden:
        await update.message.reply_text(
            "🚫 من به این کانال دسترسی ندارم!\n\n"
            "لطفاً اول من رو به کانال اضافه کن و ادمین کن (با مجوز ارسال پیام).",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_CHANNEL
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ خطایی پیش اومد: {str(e)}\nدوباره تلاش کن.",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_CHANNEL

    # چک کردن اینکه ربات ادمین هست یا نه
    try:
        chat_member = await bot.get_chat_member(chat_id, bot.id)
        if chat_member.status not in ('administrator', 'creator'):
            await update.message.reply_text(
                "⚠️ من در این کانال ادمین نیستم!\n\n"
                "لطفاً من رو ادمین کن (حداقل مجوز 'ارسال پیام' بده) و دوباره آیدی رو بفرست.",
                reply_markup=get_back_to_menu_button()
            )
            return SETTING_CHANNEL
    except TelegramError:
        await update.message.reply_text(
            "❌ نتونستم وضعیت خودم رو در کانال چک کنم. دوباره امتحان کن.",
            reply_markup=get_back_to_menu_button()
        )
        return SETTING_CHANNEL

    # همه چیز اوکیه! ذخیره در دیتابیس
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings:
            await update.message.reply_text("❌ اول باید تنظیمات اولیه رو انجام بدی (/start)")
            return ConversationHandler.END

        settings.send_to = "channel"
        settings.channel_id = str(chat_id)  # ذخیره به صورت string یا int بسته به مدلت
        db.commit()
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

    return ConversationHandler.END  # یا برگرد به منوی اصلی


# ==================== Handler Registration ====================

def get_channel_handlers():
    """ثبت هندلرهای مربوط به کانال"""
    return [
        CallbackQueryHandler(choose_channel_destination, pattern=r'^dest_channel$'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel_id),
        # اگر دکمه برگشت داری:
        # CallbackQueryHandler(back_to_menu, pattern=r'^back_to_menu$'),
    ]