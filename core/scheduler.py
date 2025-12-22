"""
Scheduler برای ارسال خودکار روزانه موزیک (با JobQueue تلگرام)
"""
import logging
from datetime import datetime, timedelta
import random
import pytz
from telegram.ext import JobQueue
from telegram import Bot
from telegram.error import TelegramError

from core.database import SessionLocal, User, UserSettings, UserGenre
from core.config import config
from services.music_sender import send_music_to_user

logger = logging.getLogger(__name__)


class MusicScheduler:
    """کلاس مدیریت Scheduler با JobQueue"""
    
    def __init__(self, job_queue: JobQueue):
        self.job_queue = job_queue
        logger.info("✅ Scheduler با JobQueue راه‌اندازی شد")
    
    def start(self):
        """شروع scheduler - JobQueue خودش با app شروع می‌شه"""
        self.load_all_jobs()
        logger.info("✅ Scheduler شروع به کار کرد")
    
    def shutdown(self):
        """خاموش کردن - JobQueue با app shutdown می‌شه"""
        pass  # نیازی نیست، تلگرام مدیریت می‌کنه
    
    def add_user_job(
        self,
        user_id: int,
        send_time: str,
        timezone: str = 'Asia/Tehran'
    ):
        """
        اضافه کردن job برای یک کاربر
        """
        try:
            hour, minute = map(int, send_time.split(':'))
            
            job_id = f'user_{user_id}'
            # حذف job قبلی
            existing_jobs = self.job_queue.get_jobs_by_name(job_id)
            for job in existing_jobs:
                job.schedule_removal()
            
            # محاسبه زمان اولین اجرا
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if run_time < now:
                run_time += timedelta(days=1)
            
            # اضافه کردن job روزانه
            self.job_queue.run_daily(
                callback=self.send_daily_music,
                time=run_time.time(),
                days=(0, 1, 2, 3, 4, 5, 6),  # هر روز
                name=job_id,
                data=user_id,
                chat_id=None,  # نیازی نیست
                tzinfo=tz
            )
            
            logger.info(f"✅ Job برای کاربر {user_id} اضافه شد در {send_time}")
            
        except ValueError as e:
            logger.error(f"❌ خطا در پارس زمان برای کاربر {user_id}: {e}")
    
    async def send_daily_music(self, context):
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
            send_to = settings.send_to if settings else 'private'
            channel_id = settings.channel_id if settings else None
            
            success = await send_music_to_user(
                bot=context.bot,
                user_id=user_id,
                genre=genre,
                send_to=send_to,
                channel_id=channel_id,
                download_file=True
            )
            
            if success:
                logger.info(f"✅ موزیک ارسال شد برای {user_id}")
            else:
                logger.warning(f"⚠️ ارسال ناموفق برای {user_id}")
                
        except TelegramError as e:
            logger.error(f"❌ خطا در ارسال تلگرام: {e}")
        finally:
            db.close()
    
    def load_all_jobs(self):
        """بارگذاری تمام jobها از دیتابیس"""
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()
            loaded = 0
            
            for user in users:
                if user.settings and user.settings.send_time:
                    self.add_user_job(
                        user.user_id,
                        user.settings.send_time,
                        user.settings.timezone
                    )
                    loaded += 1
            
            logger.info(f"✅ {loaded} job از دیتابیس بارگذاری شد")
            
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری jobs: {e}")
        finally:
            db.close()

# ==================== Helper Functions ====================

def setup_scheduler(job_queue: JobQueue) -> MusicScheduler:
    scheduler = MusicScheduler(job_queue)
    scheduler.start()
    return scheduler