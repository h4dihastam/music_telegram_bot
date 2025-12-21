"""
تنظیمات اصلی پروژه
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# پیدا کردن مسیر root پروژه
BASE_DIR = Path(__file__).resolve().parent.parent

# بارگذاری .env
load_dotenv(BASE_DIR / '.env')


class Config:
    """کلاس تنظیمات برنامه"""
    
    # Telegram Bot
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Spotify API
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    # Musixmatch API
    MUSIXMATCH_API_KEY = os.getenv('MUSIXMATCH_API_KEY')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///music_bot.db')
    
    # تنظیمات زمانی
    DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'Asia/Tehran')
    
    # مسیرها
    DATA_DIR = BASE_DIR / 'data'
    DOWNLOADS_DIR = BASE_DIR / 'downloads'
    
    # فایل ژانرها
    GENRES_FILE = DATA_DIR / 'genres.json'
    
    # تنظیمات Scheduler
    SCHEDULER_TIMEZONE = DEFAULT_TIMEZONE
    
    # تنظیمات دانلود موزیک
    MAX_DOWNLOAD_SIZE_MB = 50  # حداکثر حجم دانلود (مگابایت)
    DOWNLOAD_QUALITY = 'bestaudio'  # کیفیت دانلود
    
    @classmethod
    def validate(cls):
        """بررسی وجود تنظیمات ضروری"""
        required = ['BOT_TOKEN']
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            raise ValueError(f"❌ این متغیرها در .env موجود نیستند: {', '.join(missing)}")
        
        # ساخت پوشه‌های لازم
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.DOWNLOADS_DIR.mkdir(exist_ok=True)
        
        print("✅ تنظیمات با موفقیت بارگذاری شد")
        return True


# برای استفاده راحت‌تر
config = Config()