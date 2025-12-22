# استفاده از Python 3.11 slim image
FROM python:3.11-slim

# تنظیم working directory
WORKDIR /app

# نصب FFmpeg و dependencies سیستمی
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# کپی فایل requirements
COPY requirements.txt .

# نصب Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# کپی تمام فایل‌های پروژه
COPY . .

# ساخت پوشه‌های لازم
RUN mkdir -p downloads data

# تنظیم متغیر محیطی برای Python
ENV PYTHONUNBUFFERED=1

# Health check (اختیاری - برای Render خوبه)
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# اجرای ربات
CMD ["python", "main.py"]