"""
Scheduler برای ارسال خودکار روزانه موزیک (با JobQueue تلگرام - نسخه نهایی بدون load_all_jobs)
"""
import logging
from datetime import datetime, timedelta
import random
import pytz
from telegram.ext import JobQueue, ContextTypes
from telegram.error import TelegramError

from core.database import SessionLocal, UserGenre, UserSettings
from core.config import config
from services.music_sender import send_music_to_user

logger = logging.getLogger(__name__)


class MusicScheduler:
    """کلاس مدیریت Scheduler با JobQueue"""
    
    def __init__(self, job_queue: JobQueue):
        self.job_queue = job_queue
        logger.info("✅ Scheduler با JobQueue راه‌اندازی شد")
    
    def start(self):
        # دیگه load_all_jobs نداریم — jobها موقع ذخیره تنظیمات کاربر اضافه می‌شن
        logger.info("✅ Scheduler شروع به کار کرد (jobها موقع تنظیم کاربر اضافه می‌شن)")

    def add_or_update_user_job(
        self,
        user_id: int,
        send_time: str,
        timezone: str = 'Asia/Tehran'
    ):
        """
        اضافه یا به‌روزرسانی job برای یک کاربر
        این تابع رو از handlerهای تنظیمات صدا بزن (مثل بعد از ذخیره زمان یا ژانر)
        """
        try:
            hour, minute = map(int, send_time.split(':'))
            
            job_id = f'user_{user_id}'
            
            # حذف job قبلی اگر وجود داشت
            existing_jobs = self.job_queue.get_jobs_by_name(job_id)
            for job in existing_jobs:
                job.schedule_removal()
            
            # محاسبه زمان اولین اجرا
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if run_time <= now:
                run_time += timedelta(days=1)
            
            # اضافه کردن job روزانه
            self.job_queue.run_daily(
                callback=self.send_daily_music,
                time=run_time.time(),
                days=(0, 1, 2, 3, 4, 5, 6),
                name=job_id,
                data=user_id,
                tzinfo=tz
            )
            
            logger.info(f"✅ Job روزانه برای کاربر {user_id} در {send_time} ({timezone}) اضافه/به‌روزرسانی شد")
            
        except Exception as e:
            logger.error(f"❌ خطا در اضافه کردن job برای کاربر {user_id}: {e}")

    async def send_daily_music(self, context: ContextTypes.DEFAULT_TYPE):
        """تابع callback برای ارسال روزانه"""
        user_id = context.job.data
        logger.info(f"📤 ارسال روزانه موزیک برای کاربر {user_id}")
        
        db = SessionLocal()
        try:
            genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
            if not genres:
                logger.warning(f"⚠️ هیچ ژانری برای کاربر {user_id} پیدا نشد")
                return
            
            genre = random.choice([g.genre for g in genres])
            
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if not settings:
                logger.warning(f"⚠️ تنظیمات برای کاربر {user_id} پیدا نشد")
                return
            
            send_to = settings.send_to
            channel_id = settings.channel_id if send_to == 'channel' else None
            
            success = await send_music_to_user(
                bot=context.bot,
                user_id=user_id,
                genre=genre,
                send_to=send_to,
                channel_id=channel_id,
                download_file=True
            )
            
            if success:
                logger.info(f"✅ موزیک روزانه ارسال شد برای {user_id}")
            else:
                logger.warning(f"⚠️ ارسال روزانه ناموفق برای {user_id}")
                
        except Exception as e:
            logger.error(f"❌ خطا در ارسال روزانه برای {user_id}: {e}")
        finally:
            db.close()


# ==================== Helper Functions ====================

def setup_scheduler(job_queue: JobQueue) -> MusicScheduler:
    scheduler = MusicScheduler(job_queue)
    scheduler.start()
    return scheduler


# تابع کمکی برای استفاده در handlerها (context رو بگیره تا job_queue از app بگیریم)
def schedule_user_daily_music(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    این تابع رو در handlerهایی که تنظیمات کاربر ذخیره می‌شه صدا بزن
    مثلاً بعد از db.commit در ذخیره زمان یا ژانر
    """
    from core.database import SessionLocal, UserSettings
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings and settings.send_time:
            # دسترسی به job_queue از context
            job_queue = context.application.job_queue
            scheduler = setup_scheduler(job_queue)
            scheduler.add_or_update_user_job(
                user_id=user_id,
                send_time=settings.send_time,
                timezone=settings.timezone or 'Asia/Tehran'
            )
    finally:
        db.close()