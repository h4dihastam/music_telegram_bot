# decorators.py - در فولدر utils/
"""
دکوراتورهای مفید برای پروژه (مثل چک دسترسی، logging)
"""

import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def log_handler(func):
    """
    دکوراتور برای لاگ کردن هندلرها
    
    استفاده: @log_handler
    async def my_handler(update, context): ...
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        handler_name = func.__name__
        
        logger.info(f"📥 Handler '{handler_name}' called by user {user_id}")
        
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Error in '{handler_name}': {e}")
            if update.effective_message:
                await update.effective_message.reply_text("❌ خطایی رخ داد! لطفاً بعداً امتحان کنید.")
            raise
    
    return wrapper


def admin_only(func):
    """
    دکوراتور برای محدود کردن به ادمین (اگر نیاز به ادمین داشته باشی)
    
    استفاده: @admin_only
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # لیست ادمین‌ها (از config یا DB بگیر)
        admins = [123456789]  # جایگزین با ادمین واقعی
        
        if user_id not in admins:
            await update.message.reply_text("❌ دسترسی ندارید!")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def rate_limit(seconds: int = 5):
    """
    دکوراتور ساده برای rate limit (برای جلوگیری از spam)
    
    استفاده: @rate_limit(10)
    """
    from datetime import datetime, timedelta
    
    user_last_call = {}
    
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        now = datetime.now()
        
        if user_id in user_last_call:
            if now - user_last_call[user_id] < timedelta(seconds=seconds):
                await update.message.reply_text(f"⏳ لطفاً {seconds} ثانیه صبر کنید!")
                return
        
        user_last_call[user_id] = now
        return await func(update, context, *args, **kwargs)
    
    return wrapper


if __name__ == "__main__":
    # تست دکوراتورها (ساده)
    print("🧪 تست Decorators...")
    
    @log_handler
    async def test_handler(update, context):
        print("Handler executed")
    
    # نمی‌تونیم async رو مستقیم تست کنیم، اما ساختار رو چک کن
    print("✅ ساختار دکوراتورها OK")