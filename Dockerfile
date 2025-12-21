# استفاده از Python 3.11 slim image
FROM python:3.11-slim

# تنظیم working directory
WORKDIR /app

# نصب FFmpeg (برای yt-dlp)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# کپی فایل‌های requirements
COPY requirements.txt .

# نصب dependencies
RUN pip install --no-cache-dir -r requirements.txt

# کپی تمام فایل‌های پروژه
COPY . .

# ساخت پوشه downloads
RUN mkdir -p downloads data

# اجرای ربات
CMD ["python", "main.py"]