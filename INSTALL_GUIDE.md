# 🔧 راهنمای رفع مشکلات و بهبود ربات

## مشکلات شناسایی شده و راه‌حل‌ها:

### 1️⃣ مشکل: دانلود ناقص فایل‌ها

**علت:**
- Timeout کم در yt-dlp
- عدم فیلتر فایل‌های کوچک (preview اشتباهی)

**راه‌حل:**
```bash
# جایگزین کردن فایل downloader.py
cp /home/claude/downloader_fixed.py services/downloader.py
```

**تغییرات اعمال شده:**
- افزایش timeout به 90 ثانیه
- اضافه کردن `--match-filter 'duration > 60'` برای فیلتر ویدیوهای کوتاه
- چک حجم فایل: حداقل 500KB (حدود 30 ثانیه با کیفیت متوسط)
- افزایش تلاش‌ها: `--retries 5` و `--fragment-retries 10`
- بهبود استراتژی جستجو: 3 query مختلف

---

### 2️⃣ مشکل: نبود آهنگ فارسی

**علت:**
- لیست هنرمندان فارسی محدود
- کلمات کلیدی ناکافی

**راه‌حل:**
```bash
# جایگزین کردن فایل spotify.py
cp /home/claude/spotify_fixed.py services/spotify.py

# جایگزین کردن genres.json
cp /home/claude/genres.json data/genres.json
```

**تغییرات اعمال شده:**
- اضافه کردن 30+ هنرمند فارسی در هر ژانر
- 3 ژانر فارسی جدید:
  - `persian_pop` (پاپ فارسی) 🇮🇷
  - `persian_traditional` (سنتی/اصیل) 🇮🇷
  - `persian_rap` (رپ فارسی) 🇮🇷
- افزایش تعداد آهنگ‌های جستجو شده: 50 → 100
- بهبود الگوریتم جستجو برای موزیک فارسی

---

### 3️⃣ مشکل: تکرار آهنگ‌ها

**علت:**
- exclude list کوچک (100 آهنگ)
- Pool کم آهنگ‌ها

**راه‌حل:**
فایل spotify_fixed.py این مشکل را حل کرده:

**تغییرات:**
- افزایش exclude list: 100 → 200 آهنگ
- افزایش pool جستجو: 50 → 100 آهنگ
- اگر همه آهنگ‌ها تکراری شدند، از اول شروع می‌کند (بجای خطا)

---

### 4️⃣ مشکل: خطا بعد از 3-4 روز

**علت‌های محتمل:**
1. دیسک پُر شده (فایل‌های دانلود پاک نشده)
2. Token Spotify منقضی شده
3. Rate limit API

**راه‌حل:**

#### الف) پاکسازی خودکار فایل‌ها:
```python
# در downloader_fixed.py فعال شده:
# هر 2 ساعت فایل‌های قدیمی پاک می‌شوند
cleanup_old_files(max_age_hours=2)
```

#### ب) لاگ بهتر:
```bash
# چک کردن لاگ‌ها
tail -100 bot.log | grep -i error

# یا در Render:
Dashboard → Logs → فیلتر "ERROR"
```

#### ج) Monitoring بهتر:
اضافه کردن به `main.py`:
```python
import schedule

async def cleanup_task():
    """پاکسازی روزانه"""
    from services.downloader import music_downloader
    music_downloader.cleanup_old_files(max_age_hours=6)
    logger.info("🗑️ Cleanup completed")

# اضافه کردن به scheduler
scheduler.run_daily(cleanup_task, time=dt_time(3, 0))  # هر شب 3 صبح
```

---

### 5️⃣ اضافه کردن قابلیت جستجو

**راه‌حل:**
```bash
# کپی کردن handler جدید
cp /home/claude/search_handler.py bot/handlers/search.py
```

سپس در `main.py`:
```python
from bot.handlers.search import get_search_conversation_handler

# در تابع main_async():
search_handler = get_search_conversation_handler()
app.add_handler(search_handler)
```

**استفاده:**
```
کاربر: /search
ربات: اسم آهنگ یا خواننده رو بنویس
کاربر: Blinding Lights
ربات: [نمایش 10 نتیجه با دکمه‌های انتخاب]
کاربر: [کلیک روی آهنگ]
ربات: [دانلود و ارسال]
```

---

## 📝 Checklist نصب کامل:

```bash
# 1. جایگزین کردن فایل‌های اصلی
cp /home/claude/downloader_fixed.py services/downloader.py
cp /home/claude/spotify_fixed.py services/spotify.py
cp /home/claude/genres.json data/genres.json
cp /home/claude/search_handler.py bot/handlers/search.py

# 2. بروزرسانی main.py
# (افزودن search handler - دستورالعمل بالا)

# 3. تست
python test_download.py

# 4. اجرا
python main.py
```

---

## 🧪 تست کردن تغییرات:

### تست 1: دانلود کامل
```bash
python test_download.py
# باید فایل بیشتر از 500KB دانلود بشه
```

### تست 2: آهنگ فارسی
```
/start
# انتخاب: پاپ فارسی یا رپ فارسی
# باید آهنگ فارسی بیاد
```

### تست 3: جستجو
```
/search
Shadmehr Aghili
# باید لیست آهنگ‌های شادمهر نمایش بده
```

### تست 4: عدم تکرار
```
# برای 10 روز متوالی چک کن
# نباید آهنگ تکراری بیاد
```

---

## 📊 Monitoring

### چک کردن فضای دیسک:
```bash
du -sh downloads/
# باید زیر 100MB باشه
```

### چک کردن تعداد فایل:
```bash
ls downloads/ | wc -l
# باید زیر 20 فایل باشه
```

### چک کردن لاگ خطاها:
```bash
grep -i "error\|failed" bot.log | tail -20
```

---

## ⚙️ تنظیمات پیشنهادی محیط:

### Render:
```yaml
# render.yaml
services:
  - type: web
    disk:
      sizeGB: 2  # افزایش به 2GB
    
    envVars:
      - key: CLEANUP_INTERVAL_HOURS
        value: "2"
```

### .env:
```env
# اضافه کردن:
MAX_DOWNLOAD_SIZE_MB=10
CLEANUP_OLD_FILES_HOURS=2
MAX_EXCLUDE_TRACKS=200
```

---

## 🚨 اگر مشکل حل نشد:

1. **Restart کامل:**
```bash
# Local:
pkill python
python main.py

# Render:
Dashboard → Manual Deploy
```

2. **پاک کردن دیتابیس آهنگ‌های قدیمی:**
```python
from core.database import SessionLocal, SentTrack
from datetime import datetime, timedelta

db = SessionLocal()
old_date = datetime.now() - timedelta(days=30)
db.query(SentTrack).filter(SentTrack.sent_at < old_date).delete()
db.commit()
```

3. **چک کردن Spotify credentials:**
```bash
python -c "from services.spotify import spotify_service; print(spotify_service.is_available())"
# باید True برگردونه
```

---

## 📞 پشتیبانی

اگر بعد از این تغییرات مشکل داشتید:
1. لاگ کامل رو بفرستید: `tail -500 bot.log`
2. خروجی `python test_download.py`
3. نسخه Python: `python --version`
4. محیط: Local یا Render؟

---

**آخرین بروزرسانی:** ژانویه 2026
**نسخه:** 2.0 - با آهنگ فارسی و جستجو
