# helpers.py - در فولدر utils/
"""
توابع کمکی عمومی برای پروژه - FIXED
"""

import re
from datetime import datetime
from typing import Optional, Tuple

from core.config import config


def validate_time_format(time_str: str) -> bool:
    """
    اعتبارسنجی فرمت زمان HH:MM - FIXED
    
    Args:
        time_str: رشته زمان (مثل "09:30")
    
    Returns:
        True اگر فرمت درست باشه، False اگر نه
    """
    # چک فرمت کلی
    if not re.match(r'^([01]?\d|2[0-3]):([0-5]\d)$', time_str):
        return False
    
    try:
        hour, minute = map(int, time_str.split(':'))
        # چک محدوده
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return True
    except:
        return False
    
    return False


def parse_time(time_str: str) -> Optional[Tuple[int, int]]:
    """
    تبدیل رشته زمان به tuple (hour, minute)
    
    Args:
        time_str: رشته زمان
    
    Returns:
        (ساعت, دقیقه) یا None
    """
    if not validate_time_format(time_str):
        return None
    
    try:
        hour, minute = map(int, time_str.split(':'))
        return (hour, minute)
    except:
        return None


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
    # حذف کاراکترهای غیرمجاز
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # جایگزینی فاصله با _
    filename = re.sub(r'\s+', '_', filename)
    return filename[:200]  # محدود کردن طول


if __name__ == "__main__":
    # تست helpers
    print("🧪 تست Helpers...")
    
    print("\n1. Time validation:")
    print(f"  '09:30' -> {validate_time_format('09:30')}")  # True
    print(f"  '25:00' -> {validate_time_format('25:00')}")  # False
    print(f"  '9:30' -> {validate_time_format('9:30')}")    # True
    print(f"  'invalid' -> {validate_time_format('invalid')}")  # False
    
    print("\n2. Parse time:")
    print(f"  '14:45' -> {parse_time('14:45')}")  # (14, 45)
    print(f"  '25:00' -> {parse_time('25:00')}")  # None
    
    print("\n3. Duration:")
    print(f"  123456ms -> {format_duration(123456)}")  # 02:03
    
    print("\n4. Current time:")
    print(f"  {get_current_time()}")
    
    print("\n5. Sanitize:")
    test_name = "Song: Name! @ Artist.mp3"
    print(f"  '{test_name}' -> '{sanitize_filename(test_name)}'")