FROM python:3.11-slim

WORKDIR /app

# نصب FFmpeg و dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# کپی requirements
COPY requirements.txt .

# آپگرید pip اول
RUN pip install --no-cache-dir --upgrade pip

# نصب dependencies
RUN pip install --no-cache-dir -r requirements.txt

# کپی پروژه
COPY . .

# ساخت فولدرها
RUN mkdir -p downloads data

# متغیرهای محیطی
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check برای Render
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# اجرا
CMD ["python", "-u", "main.py"]