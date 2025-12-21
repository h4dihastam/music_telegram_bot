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
        InlineKeyboardButton("✔️ تأیید و ادامه", callback_data="genre_confirm")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت", callback_data="menu_back")
    ])
    
    return InlineKeyboardMarkup(keyboard)


async def show_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=True):
    """نمایش منوی انتخاب ژانر"""
    user_id = update.effective_user.id
    
    # گرفتن ژانرهای فعلی کاربر
    db = SessionLocal()
    try:
        current_genres = {
            ug.genre for ug in db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        }
    finally:
        db.close()
    
    # ذخیره در context برای استفاده بعدی
    if 'selected_genres' not in context.user_data:
        context.user_data['selected_genres'] = current_genres.copy()
    
    keyboard = get_genres_keyboard(context.user_data['selected_genres'])
    
    text = "🎵 ژانرهای مورد علاقه‌ات رو انتخاب کن:\n\nمی‌تونی چندتا انتخاب کنی!\n(دوباره بزن تا لغو بشه)"

    if update.callback_query and edit:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text=text, reply_markup=keyboard)


async def handle_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی ژانرها و تأیید"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # گرفتن مجموعه فعلی از context
    selected = context.user_data.get('selected_genres', set())
    
    if data.startswith("genre_select_"):
        genre_id = data.replace("genre_select_", "")
        
        if genre_id in selected:
            selected.remove(genre_id)
        else:
            selected.add(genre_id)
        
        context.user_data['selected_genres'] = selected
        
        # بروزرسانی کیبورد
        keyboard = get_genres_keyboard(selected)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        
    elif data == "genre_confirm":
        # تأیید نهایی و ذخیره در دیتابیس
        db = SessionLocal()
        try:
            # حذف قبلی‌ها
            db.query(UserGenre).filter(UserGenre.user_id == user_id).delete()
            
            # اضافه کردن جدیدها
            for genre_id in selected:
                db.add(UserGenre(user_id=user_id, genre=genre_id))
            
            db.commit()
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
        
        # اگر در فرآیند /start بودی، می‌تونی به مرحله بعدی بری
        # (اینجا فقط برگشت به منو داریم)


# ==================== Handler Registration ====================

def get_genre_handlers():
    """ثبت هندلرهای مربوط به ژانر"""
    return [
        CallbackQueryHandler(
            show_genre_selection,
            pattern=r'^menu_change_genre$'  # از منوی تنظیمات
        ),
        CallbackQueryHandler(
            handle_genre_selection,
            pattern=r'^(genre_select_|genre_confirm)'
        ),
    ]