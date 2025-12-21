"""
کیبوردهای Inline برای ربات
"""

import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pathlib import Path


# مسیر فایل ژانرها
GENRES_FILE = Path(__file__).parent.parent.parent / "data" / "genres.json"


def load_genres():
    """بارگذاری لیست ژانرها از JSON"""
    if not GENRES_FILE.exists():
        raise FileNotFoundError(f"فایل genres.json پیدا نشد: {GENRES_FILE}")
    
    with open(GENRES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# بارگذاری یکبار (بهینه)
GENRES_LIST = load_genres()


def get_genres_keyboard(selected_genres=None):
    """
    کیبورد انتخاب چندگانه ژانر (multi-select)
    استفاده شده در genre.py
    """
    if selected_genres is None:
        selected_genres = set()

    keyboard = []
    for genre in GENRES_LIST:
        prefix = "✅" if genre["id"] in selected_genres else "⚪"
        text = f"{prefix} {genre['name']}"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"genre_select_{genre['id']}")
        ])

    # ردیف دکمه‌های پایینی
    keyboard.append([InlineKeyboardButton("✔️ تأیید و ذخیره", callback_data="genre_confirm")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu_back")])

    return InlineKeyboardMarkup(keyboard)


def get_time_selection_keyboard():
    """کیبورد انتخاب زمان ارسال"""
    keyboard = [
        [
            InlineKeyboardButton("🌅 صبح (09:00)", callback_data="time_09:00"),
            InlineKeyboardButton("☀️ ظهر (12:00)", callback_data="time_12:00"),
        ],
        [
            InlineKeyboardButton("🌆 عصر (17:00)", callback_data="time_17:00"),
            InlineKeyboardButton("🌙 شب (21:00)", callback_data="time_21:00"),
        ],
        [
            InlineKeyboardButton("⏰ زمان دلخواه", callback_data="time_custom"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_destination_keyboard():
    """کیبورد انتخاب مقصد ارسال"""
    keyboard = [
        [
            InlineKeyboardButton("💬 همین چت (پیوی)", callback_data="dest_private"),
        ],
        [
            InlineKeyboardButton("📢 کانال تلگرام", callback_data="dest_channel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard():
    """منوی اصلی ربات"""
    keyboard = [
        [
            InlineKeyboardButton("🎵 تغییر ژانر", callback_data="menu_change_genre"),
            InlineKeyboardButton("⏰ تغییر زمان", callback_data="menu_change_time"),
        ],
        [
            InlineKeyboardButton("📍 تغییر مقصد", callback_data="menu_change_dest"),
        ],
        [
            InlineKeyboardButton("ℹ️ وضعیت فعلی", callback_data="menu_status"),
            InlineKeyboardButton("🎲 موزیک تصادفی حالا", callback_data="menu_random"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_button():
    """دکمه واحد برای برگشت به منو (استفاده در همه جا)"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 برگشت به منو", callback_data="menu_back")
    ]])


def get_confirmation_keyboard():
    """کیبورد تایید/لغو"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تأیید", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ لغو", callback_data="confirm_no"),
        ]
    ])


# توابع قدیمی رو حذف یا کامنت کن (دیگه لازم نیستن)
# get_back_button(), get_cancel_button() → از get_back_to_menu_button استفاده کن