"""
مدیریت فعال/غیرفعال کردن زمان‌بندی
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from core.database import SessionLocal, UserSettings, UserGenre
from core.scheduler import schedule_user_daily_music_helper

logger = logging.getLogger(__name__)


def get_schedule_status_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """کیبورد وضعیت زمان‌بندی"""
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        if not settings:
            return None
        
        is_enabled = settings.auto_send_enabled
        
        keyboard = []
        
        # دکمه فعال/غیرفعال
        if is_enabled:
            keyboard.append([
                InlineKeyboardButton(
                    "⏸ غیرفعال کردن ارسال خودکار",
                    callback_data="schedule_disable"
                )
            ])
            status_emoji = "✅"
        else:
            keyboard.append([
                InlineKeyboardButton(
                    "▶️ فعال کردن ارسال خودکار",
                    callback_data="schedule_enable"
                )
            ])
            status_emoji = "❌"
        
        # دکمه‌های تنظیمات
        keyboard.append([
            InlineKeyboardButton(
                "⏰ تغییر زمان",
                callback_data="menu_change_time"
            ),
            InlineKeyboardButton(
                "🎵 تغییر ژانر",
                callback_data="menu_change_genre"
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back_to_downloads"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
        
    finally:
        db.close()


async def show_schedule_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تنظیمات زمان‌بندی"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        genres = db.query(UserGenre).filter(
            UserGenre.user_id == user_id
        ).all()
        
        if not settings:
            text = "❌ تنظیماتی یافت نشد!"
            keyboard = None
        else:
            status = "✅ فعال" if settings.auto_send_enabled else "❌ غیرفعال"
            genre_list = ", ".join([g.genre for g in genres]) if genres else "انتخاب نشده"
            
            text = (
                "⏰ <b>تنظیمات زمان‌بندی</b>\n\n"
                f"وضعیت: {status}\n"
                f"⏰ زمان ارسال: {settings.send_time}\n"
                f"🎵 ژانرها: {genre_list}\n"
                f"📍 مقصد: {settings.send_to}\n"
                f"🌍 منطقه زمانی: {settings.timezone}\n\n"
            )
            
            if settings.auto_send_enabled:
                text += "ℹ️ <i>هر روز در زمان مشخص شده، یک آهنگ جدید برات ارسال میشه.</i>"
            else:
                text += "⚠️ <i>ارسال خودکار غیرفعال است. برای دریافت آهنگ، از منوی اصلی استفاده کن.</i>"
            
            keyboard = get_schedule_status_keyboard(user_id)
        
        if query:
            await query.edit_message_text(
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
    finally:
        db.close()


async def handle_schedule_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فعال/غیرفعال کردن زمان‌بندی"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user_id
        ).first()
        
        if not settings:
            await query.answer("❌ تنظیماتی یافت نشد!", show_alert=True)
            return
        
        if data == "schedule_enable":
            # چک کنیم که ژانر و زمان تنظیم شده باشه
            genres = db.query(UserGenre).filter(
                UserGenre.user_id == user_id
            ).all()
            
            if not genres:
                await query.answer(
                    "⚠️ اول باید ژانر انتخاب کنی!",
                    show_alert=True
                )
                return
            
            # فعال کردن
            settings.auto_send_enabled = True
            db.commit()
            
            # تنظیم scheduler
            scheduler = context.bot_data.get('scheduler')
            if scheduler:
                schedule_user_daily_music_helper(user_id, scheduler)
            
            await query.answer("✅ ارسال خودکار فعال شد!", show_alert=True)
            logger.info(f"✅ کاربر {user_id} زمان‌بندی رو فعال کرد")
            
        elif data == "schedule_disable":
            # غیرفعال کردن
            settings.auto_send_enabled = False
            db.commit()
            
            # حذف job از scheduler
            scheduler = context.bot_data.get('scheduler')
            if scheduler and scheduler.job_queue:
                job_id = f'user_{user_id}'
                current_jobs = scheduler.job_queue.get_jobs_by_name(job_id)
                for job in current_jobs:
                    job.schedule_removal()
            
            await query.answer("⏸ ارسال خودکار غیرفعال شد!", show_alert=True)
            logger.info(f"⏸ کاربر {user_id} زمان‌بندی رو غیرفعال کرد")
        
        # بروزرسانی پیام
        await show_schedule_settings(update, context)
        
    except Exception as e:
        logger.error(f"❌ خطا در toggle زمان‌بندی: {e}", exc_info=True)
        await query.answer("❌ مشکلی پیش اومد!", show_alert=True)
        db.rollback()
    finally:
        db.close()


def get_schedule_handlers():
    """لیست handler های زمان‌بندی"""
    return [
        CallbackQueryHandler(
            handle_schedule_toggle,
            pattern=r'^schedule_(enable|disable)$'
        ),
        CallbackQueryHandler(
            show_schedule_settings,
            pattern=r'^show_schedule$'
        )
    ]