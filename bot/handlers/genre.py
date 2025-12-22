"""
Handler برای انتخاب ژانرهای موسیقی
"""
import json
import os
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler

from core.database import SessionLocal, UserGenre
from bot.keyboards.inline import get_genres_keyboard, get_time_selection_keyboard, get_back_to_menu_button
from bot.states import CHOOSING_GENRE, SETTING_TIME

GENRES_FILE = os.path.join(os.path.dirname(__file__), "../../data/genres.json")

def load_genres():
    if not os.path.exists(GENRES_FILE):
        raise FileNotFoundError(f"فایل genres.json پیدا نشد: {GENRES_FILE}")
    with open(GENRES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

GENRES_LIST = load_genres()


async def show_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=True):
    """نمایش کیبورد انتخاب ژانر"""
    query = update.callback_query if edit else None
    user_id = update.effective_user.id

    db = SessionLocal()
    try:
        current_genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        selected = set(g.genre for g in current_genres)
    finally:
        db.close()

    context.user_data['selected_genres'] = selected

    text = "🎵 ژانرهای مورد علاقه‌ات رو انتخاب کن (چندتایی OK!):\n\n" \
           "روی هر کدوم کلیک کن تا انتخاب/لغو بشه."

    if query:
        await query.answer()
        await query.edit_message_text(
            text=text,
            reply_markup=get_genres_keyboard(selected)
        )
    else:
        if update.message:
            await update.message.reply_text(
                text=text,
                reply_markup=get_genres_keyboard(selected)
            )


async def handle_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی ژانرها"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("genre_select_"):
        genre_id = data.split("_")[-1]
        selected = context.user_data.get('selected_genres', set())

        if genre_id in selected:
            selected.remove(genre_id)
        else:
            selected.add(genre_id)

        context.user_data['selected_genres'] = selected

        await query.edit_message_reply_markup(
            reply_markup=get_genres_keyboard(selected)
        )
        return CHOOSING_GENRE

    elif data == "genre_confirm":
        selected = context.user_data.get('selected_genres', set())
        
        if not selected:
            await query.answer("⚠️ حداقل یک ژانر انتخاب کن!", show_alert=True)
            return CHOOSING_GENRE
        
        user_id = update.effective_user.id

        db = SessionLocal()
        try:
            db.query(UserGenre).filter(UserGenre.user_id == user_id).delete()
            
            for genre_id in selected:
                db.add(UserGenre(user_id=user_id, genre=genre_id))
            
            db.commit()
            
            # تنظیم scheduler
            scheduler = context.bot_data.get('scheduler')
            if scheduler:
                from core.scheduler import schedule_user_daily_music_helper
                schedule_user_daily_music_helper(user_id, scheduler)
        finally:
            db.close()
        
        if 'selected_genres' in context.user_data:
            del context.user_data['selected_genres']
        
        genre_names = [g["name"] for g in GENRES_LIST if g["id"] in selected]
        genre_text = ", ".join(genre_names)
        
        # در حالت /start باید بره به انتخاب زمان
        await query.edit_message_text(
            text=f"✅ ژانرها ذخیره شدند!\n\n"
                 f"🎵 انتخاب‌ها: {genre_text}\n\n"
                 f"حالا زمان ارسال روزانه رو انتخاب کن:",
            reply_markup=get_time_selection_keyboard()
        )
        
        return SETTING_TIME

    elif data == "menu_back":
        from bot.handlers.settings import show_menu
        await show_menu(update, context)
        return ConversationHandler.END


def get_genre_handlers():
    """handlers ژانر"""
    return [
        CallbackQueryHandler(
            handle_genre_selection,
            pattern=r'^(genre_select_|genre_confirm|menu_back)'
        ),
    ]