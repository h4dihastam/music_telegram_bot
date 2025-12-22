"""
Scheduler برای ارسال خودکار روزانه موزیک
استفاده از JobQueue تلگرام
"""
import logging
from datetime import datetime, timedelta
import random
import pytz
from telegram.ext import JobQueue, ContextTypes

from core.database import SessionLocal, UserGenre, UserSettings
from core.config import config

logger = logging.getLogger(__name__)


class MusicScheduler:
    """کلاس مدیریت Scheduler با JobQueue"""
    
    def __init__(self, job_queue: JobQueue):
        """
        راه‌اندازی scheduler
        
        Args:
            job_queue: JobQueue از Application
        """
        self.job_queue = job_queue
        logger.info("✅ Scheduler با JobQueue راه‌اندازی شد")
    
    def start(self):
        """شروع scheduler - jobها موقع تنظیم کاربر اضافه می‌شن"""
        logger.info("✅ Scheduler آماده است (jobها توسط handlers اضافه می‌شن)")

    def add_or_update_user_job(
        self,
        user_id: int,
        send_time: str,
        timezone: str = 'Asia/Tehran'
    ):
        """
        اضافه یا به‌روزرسانی job روزانه برای یک کاربر
        
        Args:
            user_id: شناسه کاربر تلگرام
            send_time: زمان ارسال به فرمت HH:MM
            timezone: منطقه زمانی (پیش‌فرض Asia/Tehran)
        """
        try:
            # پارس کردن زمان
            hour, minute = map(int, send_time.split(':'))
            
            job_id = f'user_{user_id}'
            
            # حذف job قبلی اگر وجود داشت
            existing_jobs = self.job_queue.get_jobs_by_name(job_id)
            for job in existing_jobs:
                job.schedule_removal()
                logger.info(f"🗑️ Job قبلی کاربر {user_id} حذف شد")
            
            # محاسبه زمان اولین اجرا
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # اگر زمان امروز گذشته، از فردا شروع کن
            if run_time <= now:
                run_time += timedelta(days=1)
            
            # اضافه کردن job روزانه
            self.job_queue.run_daily(
                callback=self.send_daily_music,
                time=run_time.time(),
                days=(0, 1, 2, 3, 4, 5, 6),  # همه روزهای هفته
                name=job_id,
                data=user_id,
                tzinfo=tz
            )
            
            next_run = run_time.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"✅ Job روزانه برای کاربر {user_id} در {send_time} ({timezone}) تنظیم شد")
            logger.info(f"   اجرای بعدی: {next_run}")
            
        except ValueError as e:
            logger.error(f"❌ فرمت زمان نامعتبر برای کاربر {user_id}: {send_time} - {e}")
        except Exception as e:
            logger.error(f"❌ خطا در تنظیم job برای کاربر {user_id}: {e}")

    def remove_user_job(self, user_id: int):
        """
        حذف job یک کاربر
        
        Args:
            user_id: شناسه کاربر
        """
        job_id = f'user_{user_id}'
        
        try:
            existing_jobs = self.job_queue.get_jobs_by_name(job_id)
            for job in existing_jobs:
                job.schedule_removal()
            
            if existing_jobs:
                logger.info(f"✅ Job کاربر {user_id} حذف شد")
        except Exception as e:
            logger.error(f"❌ خطا در حذف job کاربر {user_id}: {e}")

    async def send_daily_music(self, context: ContextTypes.DEFAULT_TYPE):
        """
        تابع callback برای ارسال روزانه موزیک
        این تابع توسط JobQueue صدا زده می‌شه
        
        Args:
            context: Context تلگرام که شامل bot و job.data هست
        """
        user_id = context.job.data
        logger.info(f"📤 شروع ارسال روزانه موزیک برای کاربر {user_id}")
        
        db = SessionLocal()
        try:
            # گرفتن ژانرهای کاربر
            genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
            if not genres:
                logger.warning(f"⚠️ هیچ ژانری برای کاربر {user_id} پیدا نشد")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ هیچ ژانری انتخاب نکردی!\n\nاز /start استفاده کن."
                )
                return
            
            # انتخاب یک ژانر تصادفی
            genre = random.choice([g.genre for g in genres])
            logger.info(f"🎵 ژانر انتخاب شده: {genre}")
            
            # گرفتن تنظیمات کاربر
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if not settings:
                logger.warning(f"⚠️ تنظیمات برای کاربر {user_id} پیدا نشد")
                return
            
            send_to = settings.send_to
            channel_id = settings.channel_id if send_to == 'channel' else None
            
            # ارسال موزیک
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
                logger.info(f"✅ موزیک روزانه با موفقیت ارسال شد برای کاربر {user_id}")
            else:
                logger.warning(f"⚠️ ارسال روزانه ناموفق برای کاربر {user_id}")
                
        except Exception as e:
            logger.error(f"❌ خطا در ارسال روزانه برای کاربر {user_id}: {e}", exc_info=True)
            
            # تلاش برای اطلاع‌رسانی به کاربر
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ متأسفانه نتونستم امروز موزیک بفرستم!\n\n"
                         "فردا دوباره امتحان می‌کنم 🎵"
                )
            except Exception:
                pass
                
        finally:
            db.close()

    def get_next_run_time(self, user_id: int) -> str:
        """
        دریافت زمان اجرای بعدی job یک کاربر
        
        Args:
            user_id: شناسه کاربر
        
        Returns:
            زمان به صورت string یا None
        """
        job_id = f'user_{user_id}'
        jobs = self.job_queue.get_jobs_by_name(job_id)
        
        if jobs and jobs[0].next_run_time:
            return jobs[0].next_run_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return None

    def get_all_jobs_info(self) -> list:
        """دریافت لیست تمام jobs فعال"""
        jobs_info = []
        
        for job in self.job_queue.jobs():
            if job.name and job.name.startswith('user_'):
                jobs_info.append({
                    'name': job.name,
                    'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None,
                    'enabled': job.enabled
                })
        
        return jobs_info


# ==================== Helper Functions ====================

def setup_scheduler(job_queue: JobQueue) -> MusicScheduler:
    """
    راه‌اندازی scheduler
    
    این تابع در main.py صدا زده می‌شه
    
    Args:
        job_queue: JobQueue از Application.job_queue
    
    Returns:
        نمونه MusicScheduler
    """
    scheduler = MusicScheduler(job_queue)
    scheduler.start()
    return scheduler


def schedule_user_daily_music_helper(user_id: int, scheduler: MusicScheduler):
    """
    تابع کمکی برای schedule کردن موزیک روزانه یک کاربر
    
    این تابع باید در handlers بعد از ذخیره تنظیمات کاربر صدا زده بشه
    
    Args:
        user_id: شناسه کاربر
        scheduler: نمونه MusicScheduler از context.bot_data['scheduler']
    
    Usage در handlers:
        scheduler = context.bot_data.get('scheduler')
        if scheduler:
            from core.scheduler import schedule_user_daily_music_helper
            schedule_user_daily_music_helper(user_id, scheduler)
    """
    if not scheduler:
        logger.warning(f"⚠️ Scheduler موجود نیست برای schedule کردن کاربر {user_id}")
        return
    
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not settings:
            logger.warning(f"⚠️ تنظیمات برای کاربر {user_id} پیدا نشد")
            return
        
        if not settings.send_time:
            logger.warning(f"⚠️ زمان ارسال برای کاربر {user_id} تنظیم نشده")
            return
        
        # چک کردن اینکه حداقل یک ژانر انتخاب شده
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        if not genres:
            logger.warning(f"⚠️ هیچ ژانری برای کاربر {user_id} انتخاب نشده")
            return
        
        # تنظیم job
        scheduler.add_or_update_user_job(
            user_id=user_id,
            send_time=settings.send_time,
            timezone=settings.timezone or config.DEFAULT_TIMEZONE
        )
        
    except Exception as e:
        logger.error(f"❌ خطا در schedule کردن کاربر {user_id}: {e}")
    finally:
        db.close()


# ==================== Test & Debug ====================

if __name__ == "__main__":
    # تست scheduler (فقط برای debug)
    import asyncio
    from telegram.ext import Application
    
    async def test_scheduler():
        """تست ساده scheduler"""
        print("🧪 تست Scheduler...")
        
        # ساخت Application موقت
        app = Application.builder().token(config.BOT_TOKEN).build()
        
        # راه‌اندازی scheduler
        scheduler = setup_scheduler(app.job_queue)
        
        # نمایش jobs فعال
        jobs = scheduler.get_all_jobs_info()
        print(f"\n📋 {len(jobs)} job فعال:")
        for job in jobs:
            print(f"  - {job['name']}: بعدی در {job['next_run']}")
        
        print("\n✅ Scheduler تست شد")
    
    # اجرا
    try:
        asyncio.run(test_scheduler())
    except Exception as e:
        print(f"❌ خطا در تست: {e}")