"""
Handler برای انتخاب و مدیریت ژانرهای موسیقی کاربر
- نمایش لیست ژانرها از genres.json
- پشتیبانی از انتخاب چندگانه (multi-select)
- ذخیره در جدول UserGenre
"""

import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from core.database import SessionLocal, UserGenre
from bot.keyboards.inline import get_back_to_menu_button

# اضافه برای scheduler
from core.scheduler import schedule_user_daily_music


# مسیر فایل ژانرها
GENRES_FILE = os.path.join(os.path.dirname(__file__), "../../data/genres.json")

def load_genres():
    """بارگذاری لیست ژانرها از فایل JSON"""
    if not os.path.exists(GENRES_FILE):
        raise FileNotFoundError(f"فایل genres.json پیدا نشد: {GENRES_FILE}")
    
    with open(GENRES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# بارگذاری یکبار در شروع
GENRES_LIST = load_genres()


def get_genres_keyboard(selected_genres=None):
    """
    ساخت کیبورد ژانرها با نشان دادن تیک روی انتخاب‌شده‌ها
    """
    if selected_genres is None:
        selected_genres = set()
    
    keyboard = []
    for genre in GENRES_LIST:
        prefix = "✅" if genre["id"] in selected_genres else "⚪"
        button_text = f"{prefix} {genre['name']}"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"genre_select_{genre['id']}"
            )
        ])
    
    # دکمه تأیید و برگشت
    keyboard.append([
        InlineKeyboardButton("✔️ تأیید و ذخیره", callback_data="genre_confirm")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu_back")
    ])

    return InlineKeyboardMarkup(keyboard)


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
        await update.message.reply_text(
            text=text,
            reply_markup=get_genres_keyboard(selected)
        )


async def handle_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    elif data == "genre_confirm":
        selected = context.user_data.get('selected_genres', set())
        user_id = update.effective_user.id

        db = SessionLocal()
        try:
            # حذف قبلی‌ها
            db.query(UserGenre).filter(UserGenre.user_id == user_id).delete()
            
            # اضافه کردن جدیدها
            for genre_id in selected:
                db.add(UserGenre(user_id=user_id, genre=genre_id))
            
            db.commit()

            # اضافه کردن/بروزرسانی job روزانه بعد از ذخیره ژانر
            schedule_user_daily_music(user_id)
        finally:
            db.close()
        
        # پاک کردن از context
        if 'selected_genres' in context.user_data:
            del context.user_data['selected_genres']
        
        genre_names = [g["name"] for g in GENRES_LIST if g["id"] in selected]
        genre_text = ", ".join(genre_names) if genre_names else "هیچ‌کدام"
        
        await query.edit_message_text(
            text=f"✅ ژانرها با موفقیت ذخیره شدند!\n\n"
                 f"🎵 انتخاب‌های تو: {genre_text}\n\n"
                 f"هر روز بر اساس این سلیقه برات موزیک میفرستم 🎶",
            reply_markup=get_back_to_menu_button()
        )


# ==================== Handler Registration ====================

def get_genre_handlers():
    """ثبت هندلرهای مربوط به ژانر"""
    return [
        CallbackQueryHandler(
            show_genre_selection,
            pattern=r'^menu_change_genre$'
        ),
        CallbackQueryHandler(
            handle_genre_selection,
            pattern=r'^(genre_select_|genre_confirm)'
        ),
    ]