"""
Handler برای منوی اصلی با دکمه‌های Reply
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.keyboards.reply import (
    get_main_menu_reply_keyboard,
    get_search_menu_keyboard,
    get_downloads_menu_keyboard
)
from core.database import SessionLocal, UserGenre, LikedTrack, DownloadedTrack, UserSettings

logger = logging.getLogger(__name__)


async def handle_main_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های منوی اصلی و زیرمنوهای Reply."""
    text = update.message.text

    menu_state = context.user_data.get('menu_state', 'main')
    if menu_state == 'search' and text not in {"🔍 جستجوی سریع", "🔙 برگشت", "🔙 برگشت به منو"}:
        await handle_search_menu_buttons(update, context)
        return
    if menu_state == 'downloads' and text not in {"📥 دانلودهای من", "🔙 برگشت به منو"}:
        await handle_downloads_menu_buttons(update, context)
        return

    user_id = update.effective_user.id
    
    # 🔍 جستجوی سریع
    if text == "🔍 جستجوی سریع":
        await update.message.reply_text(
            "🔍 <b>جستجوی سریع موزیک</b>\n\n"
            "چطوری می‌خوای جستجو کنی؟",
            parse_mode='HTML',
            reply_markup=get_search_menu_keyboard()
        )
        context.user_data['menu_state'] = 'search'
    
    # 🎲 پخش زنده (موزیک تصادفی)
    elif text == "🎲 پخش زنده":
        await send_random_music_now(update, context)
    
    # 🔥 جدیدترین‌ها
    elif text == "🔥 جدیدترین‌ها":
        await show_latest_tracks(update, context)
    
    # 💎 پردانلودترین‌ها
    elif text == "💎 پردانلودترین‌ها":
        await show_popular_tracks(update, context)
    
    # 📥 دانلودهای من
    elif text == "📥 دانلودهای من":
        await update.message.reply_text(
            "📥 <b>دانلودهای من</b>\n\n"
            "انتخاب کن:",
            parse_mode='HTML',
            reply_markup=get_downloads_menu_keyboard()
        )
        context.user_data['menu_state'] = 'downloads'
    
    # ℹ️ آموزش
    elif text == "ℹ️ آموزش":
        await show_tutorial(update, context)
    
    # برگشت به منو
    elif text == "🔙 برگشت به منو" or text == "🔙 برگشت":
        await update.message.reply_text(
            "🏠 منوی اصلی:",
            reply_markup=get_main_menu_reply_keyboard()
        )
        context.user_data['menu_state'] = 'main'


async def handle_search_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های منوی جستجو"""
    text = update.message.text
    
    # 📝 لینک اینستاگرام
    if text == "📝 لینک اینستاگرام":
        await update.message.reply_text(
            "📱 <b>دانلود از اینستاگرام</b>\n\n"
            "لینک پست اینستاگرام رو برام بفرست:\n"
            "مثال: https://instagram.com/p/...",
            parse_mode='HTML'
        )
        context.user_data['waiting_for'] = 'instagram_link'
    
    # 🎤 ویس یا متن آهنگ
    elif text == "🎤 ویس یا متن قسمتی از آهنگ":
        await update.message.reply_text(
            "🎤 <b>تشخیص آهنگ</b>\n\n"
            "یکی از اینها رو بفرست:\n\n"
            "• یه ویس از آهنگ\n"
            "• یه قسمت از متن آهنگ\n\n"
            "<i>من سعی می‌کنم پیداش کنم!</i>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for'] = 'voice_or_lyrics'
    
    # 🎧 ارسال فایل آهنگ
    elif text == "🎧 ارسال فایل آهنگ":
        await update.message.reply_text(
            "🎧 <b>تشخیص آهنگ از فایل</b>\n\n"
            "یک فایل صوتی یا آهنگ کوتاه بفرست تا شناسایی کنم و نسخه قابل ارسالش رو پیدا کنم.",
            parse_mode='HTML'
        )
        context.user_data['waiting_for'] = 'audio_file'

    # 🎬 کلیپ حاوی آهنگ
    elif text == "🎬 کلیپ حاوی آهنگ":
        await update.message.reply_text(
            "🎬 <b>تشخیص آهنگ از کلیپ</b>\n\n"
            "یه ویدیو که آهنگ توش باشه رو برام بفرست\n\n"
            "<i>فقط یادت باشه که حجمش زیاد نباشه!</i>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for'] = 'video_clip'
    
    # 📜 اسم آهنگ یا خواننده
    elif text == "📜 اسم آهنگ یا خواننده":
        await update.message.reply_text(
            "📜 <b>جستجو با نام</b>\n\n"
            "اسم آهنگ یا خواننده رو بنویس:\n"
            "مثال: <code>Blinding Lights</code>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for'] = 'track_name'
    
    # برگشت
    elif text == "🔙 برگشت به منو اصلی":
        await update.message.reply_text(
            "🏠 منوی اصلی:",
            reply_markup=get_main_menu_reply_keyboard()
        )
        context.user_data['menu_state'] = 'main'
        context.user_data.pop('waiting_for', None)


async def handle_downloads_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های منوی دانلودها"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # ❤️ آهنگ‌های لایک شده
    if text == "❤️ آهنگ‌های لایک شده":
        await show_liked_tracks(update, context)
    
    # 📥 تاریخچه دانلود
    elif text == "📥 تاریخچه دانلود":
        await show_download_history(update, context)
    
    # 🎵 ژانرهای من
    elif text == "🎵 ژانرهای من":
        await show_my_genres(update, context)
    
    # ⏰ زمان‌بندی
    elif text == "⏰ زمان‌بندی":
        await show_schedule_settings(update, context)
    
    # برگشت
    elif text == "🔙 برگشت":
        await update.message.reply_text(
            "🏠 منوی اصلی:",
            reply_markup=get_main_menu_reply_keyboard()
        )
        context.user_data['menu_state'] = 'main'


# ==================== Helper Functions ====================

async def send_random_music_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال موزیک تصادفی الان"""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        
        if not genres:
            await update.message.reply_text(
                "❌ هنوز ژانری انتخاب نکردی!\n\n"
                "/start بزن تا شروع کنیم."
            )
            return
        
        import random
        genre = random.choice([g.genre for g in genres])
    finally:
        db.close()
    
    msg = await update.message.reply_text(
        "🎵 در حال پیدا کردن آهنگ تصادفی...\n⏳ صبر کن..."
    )
    
    from services.music_sender import send_music_to_user
    success = await send_music_to_user(
        bot=context.bot,
        user_id=user_id,
        genre=genre,
        send_to='private',
        download_file=True
    )
    
    if success:
        await msg.edit_text("✅ آهنگ ارسال شد! 🎉")
    else:
        await msg.edit_text("❌ نتونستم آهنگ پیدا کنم!")


async def show_liked_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آهنگ‌های لایک شده"""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        liked = db.query(LikedTrack).filter(
            LikedTrack.user_id == user_id
        ).order_by(LikedTrack.liked_at.desc()).limit(20).all()
        
        if not liked:
            await update.message.reply_text(
                "💔 هنوز آهنگی لایک نکردی!\n\n"
                "وقتی آهنگی بهت ارسال میشه، می‌تونی لایکش کنی.",
                parse_mode='HTML'
            )
            return
        
        text = "❤️ <b>آهنگ‌های لایک شده شما:</b>\n\n"
        for idx, track in enumerate(liked, 1):
            text += f"{idx}. 🎵 {track.track_name}\n"
            text += f"   🎤 {track.artist}\n\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    finally:
        db.close()


async def show_download_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تاریخچه دانلود"""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        downloads = db.query(DownloadedTrack).filter(
            DownloadedTrack.user_id == user_id
        ).order_by(DownloadedTrack.downloaded_at.desc()).limit(15).all()
        
        if not downloads:
            await update.message.reply_text(
                "📥 هنوز چیزی دانلود نکردی!",
                parse_mode='HTML'
            )
            return
        
        text = "📥 <b>آخرین دانلودها:</b>\n\n"
        for idx, dl in enumerate(downloads, 1):
            text += f"{idx}. 🎵 {dl.track_name}\n"
            text += f"   🎤 {dl.artist}\n"
            text += f"   📍 منبع: {dl.source}\n\n"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    finally:
        db.close()


async def show_my_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش ژانرهای من"""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        
        if not genres:
            await update.message.reply_text("❌ هنوز ژانری انتخاب نکردی!")
            return
        
        genre_list = ", ".join([g.genre for g in genres])
        
        await update.message.reply_text(
            f"🎵 <b>ژانرهای شما:</b>\n\n{genre_list}\n\n"
            "برای تغییر از تنظیمات استفاده کن.",
            parse_mode='HTML'
        )
    finally:
        db.close()


async def show_schedule_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تنظیمات زمان‌بندی"""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        if not settings:
            await update.message.reply_text("❌ تنظیماتی یافت نشد!")
            return
        
        status = "✅ فعال" if settings.auto_send_enabled else "❌ غیرفعال"
        
        await update.message.reply_text(
            f"⏰ <b>تنظیمات زمان‌بندی:</b>\n\n"
            f"وضعیت: {status}\n"
            f"زمان ارسال: {settings.send_time}\n"
            f"منطقه زمانی: {settings.timezone}\n\n"
            "برای تغییر از تنظیمات استفاده کن.",
            parse_mode='HTML'
        )
    finally:
        db.close()


async def show_latest_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جدیدترین آهنگ‌ها"""
    await update.message.reply_text(
        "🔥 <b>جدیدترین آهنگ‌ها</b>\n\n"
        "این قابلیت به زودی اضافه میشه! 🚀",
        parse_mode='HTML'
    )


async def show_popular_tracks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پرطرفدارترین آهنگ‌ها"""
    await update.message.reply_text(
        "💎 <b>پردانلودترین آهنگ‌ها</b>\n\n"
        "این قابلیت به زودی اضافه میشه! 🚀",
        parse_mode='HTML'
    )


async def show_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آموزش"""
    tutorial_text = """
ℹ️ <b>آموزش استفاده از ربات</b>

<b>🔍 جستجو:</b>
• لینک اینستاگرام بفرست
• ویس از آهنگ بفرست
• اسم آهنگ رو بنویس

<b>❤️ لایک:</b>
• وقتی آهنگی میاد، دکمه ❤️ رو بزن

<b>⏰ زمان‌بندی:</b>
• می‌تونی ارسال خودکار رو فعال/غیرفعال کنی
• زمان دلخواه تنظیم کن

<b>📥 دانلودها:</b>
• همه دانلودهات ذخیره میشه
• می‌تونی دوباره ببینیشون

<i>موفق باشی! 🎵</i>
    """
    
    await update.message.reply_text(
        tutorial_text,
        parse_mode='HTML'
    )


def get_main_menu_handlers():
    """لیست handlerهای منوی اصلی"""
    return [
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_main_menu_buttons
        )
    ]