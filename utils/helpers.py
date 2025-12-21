# helpers.py - در فولدر utils/
"""
توابع کمکی عمومی برای پروژه
"""

import re
from datetime import datetime
from typing import Optional, Tuple

from core.config import config


def validate_time_format(time_str: str) -> Optional[Tuple[int, int]]:
    """
    اعتبارسنجی فرمت زمان HH:MM
    
    Args:
        time_str: رشته زمان
    
    Returns:
        (ساعت, دقیقه) یا None
    """
    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str):
        return None
    
    hour, minute = map(int, time_str.split(':'))
    return hour, minute


def format_duration(milliseconds: int) -> str:
    """
    تبدیل میلی‌ثانیه به فرمت MM:SS
    
    Args:
        milliseconds: مدت زمان
    
    Returns:
        رشته MM:SS
    """
    seconds = milliseconds // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def get_current_time(timezone: str = config.DEFAULT_TIMEZONE) -> datetime:
    """
    دریافت زمان فعلی با timezone
    
    Args:
        timezone: نام timezone
    
    Returns:
        datetime فعلی
    """
    import pytz
    return datetime.now(pytz.timezone(timezone))


def sanitize_filename(filename: str) -> str:
    """
    پاکسازی نام فایل برای ذخیره‌سازی
    
    Args:
        filename: نام فایل
    
    Returns:
        نام پاکسازی شده
    """
    return re.sub(r'[^\w\.-]', '_', filename)


if __name__ == "__main__":
    # تست helpers
    print("🧪 تست Helpers...")
    
    print("Time validation:")
    print(validate_time_format("09:30"))  # (9, 30)
    print(validate_time_format("25:00"))  # None
    
    print("\nDuration:")
    print(format_duration(123456))  # 02:03
    
    print("\nCurrent time:")
    print(get_current_time())
    
    print("\nSanitize:")
    print(sanitize_filename("Song Name! @ Artist.mp3"))  # Song_Name___Artist.mp3