"""
کیبوردهای Reply - مثل ربات‌های حرفه‌ای
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_reply_keyboard():
    """منوی اصلی با دکمه‌های Reply - مثل عکس"""
    keyboard = [
        [
            KeyboardButton("🔍 جستجوی سریع"),
            KeyboardButton("🎲 پخش زنده"),
        ],
        [
            KeyboardButton("🔥 جدیدترین‌ها"),
            KeyboardButton("💎 پردانلودترین‌ها"),
        ],
        [
            KeyboardButton("🎈 پیشنهادی: پاروی بی قایق"),
            KeyboardButton("💘 موزیک های محبوب اطراف شما"),
        ],
        [
            KeyboardButton("📺 ناشناس"),
            KeyboardButton("📋 پلی لیست‌ها"),
        ],
        [
            KeyboardButton("🌍 دنبال شده‌ها"),
            KeyboardButton("📥 دانلودهای من"),
        ],
        [
            KeyboardButton("ℹ️ آموزش"),
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_search_menu_keyboard():
    """منوی جستجو با گزینه‌های مختلف"""
    keyboard = [
        [
            KeyboardButton("📝 لینک اینستاگرام"),
            KeyboardButton("🎬 کلیپ حاوی آهنگ"),
        ],
        [
            KeyboardButton("🎤 ویس یا متن قسمتی از آهنگ"),
            KeyboardButton("📜 اسم آهنگ یا خواننده"),
        ],
        [
            KeyboardButton("🔙 برگشت به منو اصلی")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_downloads_menu_keyboard():
    """منوی دانلودها"""
    keyboard = [
        [
            KeyboardButton("❤️ آهنگ‌های لایک شده"),
            KeyboardButton("📥 تاریخچه دانلود"),
        ],
        [
            KeyboardButton("🎵 ژانرهای من"),
            KeyboardButton("⏰ زمان‌بندی"),
        ],
        [
            KeyboardButton("🔙 برگشت")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_settings_keyboard():
    """منوی تنظیمات"""
    keyboard = [
        [
            KeyboardButton("🎵 تغییر ژانر"),
            KeyboardButton("⏰ تغییر زمان"),
        ],
        [
            KeyboardButton("📍 تغییر مقصد"),
            KeyboardButton("⚙️ تنظیمات پیشرفته"),
        ],
        [
            KeyboardButton("ℹ️ وضعیت فعلی"),
            KeyboardButton("🔙 برگشت"),
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_back_keyboard():
    """فقط دکمه برگشت"""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🔙 برگشت به منو")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )