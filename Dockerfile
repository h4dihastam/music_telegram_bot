# استفاده از Python 3.11 slim image
FROM python:3.11-slim

# تنظیم working directory
WORKDIR /app

# کپی فایل‌های requirements
COPY requirements.txt .

# نصب dependencies
RUN pip install --no-cache-dir -r requirements.txt

# کپی تمام فایل‌های پروژه
COPY . .

# ساخت دیتابیس (اختیاری - اگه SQLite استفاده می‌کنی)
RUN python -c "from core.database import init_db; init_db()"

# اجرای ربات
CMD ["python", "main.py"]