FROM python:3.11-slim

WORKDIR /app

# نصب dependencies سیستمی (با curl برای yt-dlp)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    ca-certificates \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# کپی requirements
COPY requirements.txt .

# آپگرید pip
RUN pip install --no-cache-dir --upgrade pip

# نصب Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# نصب yt-dlp آخرین نسخه (مهم!)
RUN pip install --no-cache-dir -U yt-dlp

# تست yt-dlp
RUN yt-dlp --version

# کپی پروژه
COPY . .

# ساخت فولدرها
RUN mkdir -p downloads data

# متغیرهای محیطی
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# اجرا
CMD ["python", "-u", "main.py"]