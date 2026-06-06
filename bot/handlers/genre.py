"""
Handler برای انتخاب ژانرهای موسیقی - با fix خطای BadRequest
"""
import json
import os
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from telegram.error import BadRequest

from core.database import SessionLocal, UserGenre
from bot.keyboards.inline import get_genres_keyboard, get_time_selection_keyboard, get_back_to_menu_button, get_destination_keyboard
from bot.states import CHOOSING_GENRE, SETTING_TIME, CHOOSING_DESTINATION

GENRES_FILE = os.path.join(os.path.dirname(__file__), "../../data/genres.json")

def load_genres():
    if not os.path.exists(GENRES_FILE):
        raise FileNotFoundError(f"فایل genres.json پیدا نشد: {GENRES_FILE}")
    with open(GENRES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

GENRES_LIST = load_genres()


async def show_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=True):
    query = update.callback_query if edit else None
    user_id = update.effective_user.id

    db = SessionLocal()
    try:
        current_genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        selected = set(g.genre for g in current_genres)
    finally:
        db.close()

    context.user_data['selected_genres'] = selected

    text = "🎵 ژانرهای مورد علاقه‌ات رو انتخاب کن (چندتایی OK!):\n\nروی هر کدوم کلیک کن تا انتخاب/لغو بشه."

    if query:
        await query.answer()
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=get_genres_keyboard(selected)
            )
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise
    else:
        if update.message:
            await update.message.reply_text(text=text, reply_markup=get_genres_keyboard(selected))
        elif update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=get_genres_keyboard(selected)
            )


async def handle_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("genre_select_"):
        genre_id = data.split("_", 2)[-1]
        selected = context.user_data.get('selected_genres', set())

        if genre_id in selected:
            selected.remove(genre_id)
        else:
            selected.add(genre_id)

        context.user_data['selected_genres'] = selected

        # FIX: catch BadRequest اگه کیبورد تغییر نکرده
        try:
            await query.edit_message_reply_markup(
                reply_markup=get_genres_keyboard(selected)
            )
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise
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

        if context.user_data.get('setup_flow') == 'time_first':
            try:
                await query.edit_message_text(
                    text=f"✅ ژانرها ذخیره شدند!\n\n🎵 انتخاب‌ها: {genre_text}\n\nحالا مقصد ارسال روزانه رو انتخاب کن:",
                    reply_markup=get_destination_keyboard()
                )
            except BadRequest as e:
                if "not modified" not in str(e).lower():
                    raise
            return CHOOSING_DESTINATION

        try:
            await query.edit_message_text(
                text=f"✅ ژانرها ذخیره شدند!\n\n🎵 انتخاب‌ها: {genre_text}\n\nحالا زمان ارسال روزانه رو انتخاب کن:",
                reply_markup=get_time_selection_keyboard()
            )
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise
        return SETTING_TIME

    elif data == "menu_back":
        from bot.handlers.settings import show_menu
        await show_menu(update, context)
        return ConversationHandler.END


def get_genre_handlers():
    return [
        CallbackQueryHandler(
            handle_genre_selection,
            pattern=r'^(genre_select_|genre_confirm|menu_back)'
        ),
    ]
