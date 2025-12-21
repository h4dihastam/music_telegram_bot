"""
Handler برای دستور /start و فرآیند Setup اولیه
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from core.database import get_or_create_user
from bot.keyboards.inline import get_main_menu_keyboard
from bot.handlers.genre import show_genre_selection
from bot.states import SETTING_TIME, CHOOSING_DESTINATION, SETTING_CHANNEL

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

برای شروع یا تغییر تنظیمات، ژانر مورد علاقه‌ات رو انتخاب کن 👇
    """
    
    if update.message:
        await update.message.reply_text(welcome_text)
    else:
        await update.callback_query.edit_message_text(welcome_text)
    
    await show_genre_selection(update, context, edit=False)
    
    return SETTING_TIME

# بقیه handlerها (time, destination, channel) مثل قبل بمونن

# fallback مهم برای وقتی Conversation گیر می‌کنه
async def fallback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اگر Conversation گیر کرد، /start دوباره کار کنه"""
    await start_command(update, context)
    return SETTING_TIME

async def fallback_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("دوباره /start بزن تا از اول شروع کنیم.")

def get_start_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('start', start_command)],
        states={
            SETTING_TIME: [ ... ],  # stateهای قبلی
            CHOOSING_DESTINATION: [ ... ],
            SETTING_CHANNEL: [ ... ],
        },
        fallbacks=[
            CommandHandler('start', start_command),  # این مهمه!
            MessageHandler(filters.COMMAND, fallback_start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_unknown)
        ],
        per_user=True,
        per_chat=False,
        allow_reentry=True  # این خط خیلی مهمه – اجازه می‌ده دوباره وارد Conversation بشه
    )