"""
Scheduler برای ارسال خودکار روزانه موزیک
"""
import logging
from datetime import datetime, time as dt_time
import random
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from telegram.ext import JobQueue, ContextTypes

from core.database import SessionLocal, UserGenre, UserSettings
from core.config import config

logger = logging.getLogger(__name__)


class MusicScheduler:
    """کلاس مدیریت Scheduler با JobQueue"""
    
    def __init__(self, job_queue: JobQueue):
        self.job_queue = job_queue
        logger.info("✅ Scheduler با JobQueue راه‌اندازی شد")
    
    def start(self):
        logger.info("✅ Scheduler آماده است")

    def add_or_update_user_job(
        self,
        user_id: int,
        send_time: str,
        timezone: str = 'Asia/Tehran'
    ):
        """
        اضافه یا به‌روزرسانی job روزانه
        """
        try:
            hour, minute = map(int, send_time.split(':'))
            job_id = f'user_{user_id}'
            
            # حذف job قبلی
            existing_jobs = self.job_queue.get_jobs_by_name(job_id)
            for job in existing_jobs:
                job.schedule_removal()
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("send_time must be in HH:MM (00:00-23:59)")

            # ساخت time object با timezone استاندارد
            try:
                tz = ZoneInfo(timezone)
            except ZoneInfoNotFoundError:
                logger.warning(
                    f"⚠️ timezone نامعتبر '{timezone}'؛ fallback به {config.DEFAULT_TIMEZONE}"
                )
                tz = ZoneInfo(config.DEFAULT_TIMEZONE)

            job_time = dt_time(hour=hour, minute=minute, tzinfo=tz)
            
            # اضافه کردن job (بدون tzinfo در parameters)
            self.job_queue.run_daily(
                callback=self.send_daily_music,
                time=job_time,
                days=(0, 1, 2, 3, 4, 5, 6),
                name=job_id,
                data=user_id
            )
            
            logger.info(f"✅ Job روزانه برای کاربر {user_id} در {send_time} ({timezone}) تنظیم شد")
            
        except Exception as e:
            logger.error(f"❌ خطا در تنظیم job برای کاربر {user_id}: {e}")

    async def send_daily_music(self, context: ContextTypes.DEFAULT_TYPE):
        """ارسال روزانه موزیک"""
        user_id = context.job.data
        logger.info(f"📤 ارسال روزانه موزیک برای کاربر {user_id}")
        
        db = SessionLocal()
        try:
            genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
            if not genres:
                logger.warning(f"⚠️ هیچ ژانری برای کاربر {user_id} پیدا نشد")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ هیچ ژانری انتخاب نکردی!\n\nاز /start استفاده کن."
                )
                return
            
            genre = random.choice([g.genre for g in genres])
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            
            if not settings:
                return
            
            send_to = settings.send_to
            channel_id = settings.channel_id if send_to == 'channel' else None
            
            from services.music_sender import send_music_to_user
            success = await send_music_to_user(
                bot=context.bot,
                user_id=user_id,
                genre=genre,
                send_to=send_to,
                channel_id=channel_id,
                download_file=True
            )
            
            if success:
                logger.info(f"✅ موزیک روزانه ارسال شد")
            else:
                logger.warning(f"⚠️ ارسال ناموفق")
                
        except Exception as e:
            logger.error(f"❌ خطا در ارسال روزانه: {e}")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ متأسفانه نتونستم امروز موزیک بفرستم!\n\nفردا دوباره امتحان می‌کنم 🎵"
                )
            except:
                pass
        finally:
            db.close()


def setup_scheduler(job_queue: JobQueue) -> MusicScheduler:
    scheduler = MusicScheduler(job_queue)
    scheduler.start()
    return scheduler


def schedule_user_daily_music_helper(user_id: int, scheduler: MusicScheduler):
    """تابع کمکی برای schedule کردن"""
    if not scheduler:
        return
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not settings or not settings.send_time:
            return
        
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        if not genres:
            return
        
        scheduler.add_or_update_user_job(
            user_id=user_id,
            send_time=settings.send_time,
            timezone=settings.timezone or config.DEFAULT_TIMEZONE
        )
        
    except Exception as e:
        logger.error(f"❌ خطا در schedule کردن: {e}")
    finally:
        db.close()