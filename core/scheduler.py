"""
Scheduler برای ارسال خودکار روزانه موزیک
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.error import TelegramError
import pytz

from core.database import SessionLocal, User, UserSettings, UserGenre
from core.config import config

logger = logging.getLogger(__name__)


class MusicScheduler:
    """کلاس مدیریت Scheduler برای ارسال روزانه"""
    
    def __init__(self, bot: Bot):
        """
        راه‌اندازی scheduler
        
        Args:
            bot: نمونه Bot تلگرام
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=config.SCHEDULER_TIMEZONE)
        logger.info("✅ Scheduler راه‌اندازی شد")
    
    # ==================== راه‌اندازی ====================
    
    def start(self):
        """شروع scheduler"""
        # بارگذاری job های موجود از دیتابیس
        self.load_all_jobs()
        
        # شروع scheduler
        self.scheduler.start()
        logger.info("✅ Scheduler شروع به کار کرد")
    
    def shutdown(self):
        """خاموش کردن scheduler"""
        self.scheduler.shutdown()
        logger.info("⛔ Scheduler متوقف شد")
    
    # ==================== مدیریت Jobs ====================
    
    def add_user_job(
        self,
        user_id: int,
        send_time: str,
        timezone: str = 'Asia/Tehran'
    ):
        """
        اضافه کردن job برای یک کاربر
        
        Args:
            user_id: شناسه کاربر تلگرام
            send_time: زمان ارسال (فرمت HH:MM)
            timezone: منطقه زمانی
        """
        try:
            # پارس کردن زمان
            hour, minute = map(int, send_time.split(':'))
            
            # حذف job قبلی اگه وجود داشت
            job_id = f'user_{user_id}'
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # اضافه کردن job جدید
            self.scheduler.add_job(
                func=self.send_daily_music,
                trigger=CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=pytz.timezone(timezone)
                ),
                id=job_id,
                args=[user_id],
                replace_existing=True,
                misfire_grace_time=3600  # اگه 1 ساعت جا موند، باز هم اجرا کن
            )
            
            logger.info(f"✅ Job برای کاربر {user_id} اضافه شد - زمان: {send_time}")
            
        except Exception as e:
            logger.error(f"❌ خطا در اضافه کردن job: {e}")
    
    def remove_user_job(self, user_id: int):
        """
        حذف job یک کاربر
        
        Args:
            user_id: شناسه کاربر
        """
        job_id = f'user_{user_id}'
        
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"✅ Job کاربر {user_id} حذف شد")
        except Exception as e:
            logger.error(f"❌ خطا در حذف job: {e}")
    
    def load_all_jobs(self):
        """بارگذاری تمام job های کاربران از دیتابیس"""
        db = SessionLocal()
        try:
            users_with_settings = db.query(User, UserSettings).join(
                UserSettings,
                User.user_id == UserSettings.user_id
            ).filter(User.is_active == True).all()
            
            count = 0
            for user, settings in users_with_settings:
                if settings.send_time:
                    self.add_user_job(
                        user.user_id,
                        settings.send_time,
                        settings.timezone
                    )
                    count += 1
            
            logger.info(f"✅ {count} job از دیتابیس بارگذاری شد")
            
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری jobs: {e}")
        finally:
            db.close()
    
    # ==================== ارسال موزیک ====================
    
    async def send_daily_music(self, user_id: int):
        """
        ارسال موزیک روزانه به یک کاربر
        
        Args:
            user_id: شناسه کاربر تلگرام
        """
        logger.info(f"🎵 شروع ارسال موزیک روزانه برای کاربر {user_id}")
        
        db = SessionLocal()
        try:
            # گرفتن تنظیمات کاربر
            settings = db.query(UserSettings).filter(
                UserSettings.user_id == user_id
            ).first()
            
            if not settings:
                logger.warning(f"⚠️ تنظیمات برای کاربر {user_id} پیدا نشد")
                return
            
            # گرفتن ژانر کاربر
            user_genres = db.query(UserGenre).filter(
                UserGenre.user_id == user_id
            ).all()
            
            if not user_genres:
                logger.warning(f"⚠️ ژانر برای کاربر {user_id} پیدا نشد")
                await self.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ هنوز ژانر موسیقی خودت رو انتخاب نکردی!\n\n"
                         "از /start استفاده کن تا تنظیمات رو کامل کنی."
                )
                return
            
            # انتخاب یک ژانر (اولین ژانر)
            genre = user_genres[0].genre
            
            # گرفتن آهنگ تصادفی
            from services.music_sender import send_music_to_user
            await send_music_to_user(self.bot, user_id, genre, settings.send_to, settings.channel_id)
            
            logger.info(f"✅ موزیک روزانه برای کاربر {user_id} ارسال شد")
            
        except TelegramError as e:
            logger.error(f"❌ خطای تلگرام در ارسال به {user_id}: {e}")
            
            # اگه کاربر ربات رو بلاک کرده باشه
            if "bot was blocked" in str(e).lower():
                user = db.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.is_active = False
                    db.commit()
                    logger.info(f"⚠️ کاربر {user_id} غیرفعال شد (bot blocked)")
                
                # حذف job
                self.remove_user_job(user_id)
                
        except Exception as e:
            logger.error(f"❌ خطا در ارسال موزیک به {user_id}: {e}")
            
        finally:
            db.close()
    
    # ==================== مدیریت زمان ====================
    
    def get_next_run_time(self, user_id: int) -> str:
        """
        دریافت زمان اجرای بعدی job یک کاربر
        
        Args:
            user_id: شناسه کاربر
        
        Returns:
            زمان به صورت string یا None
        """
        job_id = f'user_{user_id}'
        job = self.scheduler.get_job(job_id)
        
        if job and job.next_run_time:
            return job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return None
    
    def get_all_jobs_info(self) -> list:
        """دریافت لیست تمام jobs فعال"""
        jobs_info = []
        
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jobs_info
    
    # ==================== Test & Debug ====================
    
    async def test_send_now(self, user_id: int):
        """
        تست: ارسال فوری موزیک بدون انتظار
        
        Args:
            user_id: شناسه کاربر
        """
        logger.info(f"🧪 تست ارسال فوری برای کاربر {user_id}")
        await self.send_daily_music(user_id)


# ==================== Helper Functions ====================

def setup_scheduler(bot: Bot) -> MusicScheduler:
    """
    راه‌اندازی scheduler
    
    Args:
        bot: نمونه Bot تلگرام
    
    Returns:
        نمونه MusicScheduler
    """
    scheduler = MusicScheduler(bot)
    scheduler.start()
    return scheduler


def update_user_schedule(user_id: int, send_time: str, timezone: str = 'Asia/Tehran'):
    """
    به‌روزرسانی زمان‌بندی یک کاربر
    این تابع باید بعد از تغییر تنظیمات کاربر صدا زده بشه
    
    Args:
        user_id: شناسه کاربر
        send_time: زمان ارسال جدید
        timezone: منطقه زمانی
    """
    # این تابع رو از handler ها صدا می‌زنیم
    # scheduler instance رو باید از application بگیریم
    pass


if __name__ == "__main__":
    # تست scheduler
    import asyncio
    from telegram import Bot
    
    async def test():
        print("🧪 تست Scheduler...")
        
        bot = Bot(token=config.BOT_TOKEN)
        scheduler = MusicScheduler(bot)
        
        # بارگذاری jobs
        scheduler.load_all_jobs()
        
        # نمایش jobs
        jobs = scheduler.get_all_jobs_info()
        print(f"\n📋 {len(jobs)} job فعال:")
        for job in jobs:
            print(f"  - {job['id']}: {job['next_run']}")
        
        # شروع scheduler
        scheduler.start()
        
        print("\n✅ Scheduler در حال اجرا...")
        print("⏰ منتظر زمان اجرای jobs...")
        
        # نگه داشتن برنامه
        await asyncio.sleep(60)
        
        scheduler.shutdown()
    
    asyncio.run(test())