# 🔍 راهنمای سریع دیباگ

## مشکل: فایل دانلود نمیشه (فقط لینک میاد)

### ✅ چک‌لیست سریع:

#### 1. بررسی لاگ‌ها در Render

```
Render Dashboard → Your Service → Logs
```

**چی دنبالش باشیم:**
```
✅ خوب: "✅ YouTube موفق: xxx.mp3"
❌ بد: "❌ همه روش‌های دانلود شکست خوردند"
⚠️ مشکوک: "⏱️ YouTube timeout"
```

#### 2. چک کردن yt-dlp در Container

بعد از deploy، SSH به container (اگه ممکنه) یا از test script استفاده کن:

```bash
# اگه SSH داری
yt-dlp --version
ffmpeg -version

# تست دانلود ساده
yt-dlp "ytsearch1:test music" --extract-audio --audio-format mp3 -o "test.mp3"
```

#### 3. استفاده از Test Script

فایل `test_download.py` رو local اجرا کن:

```bash
python test_download.py
```

خروجی باید باشه:
```
✅ yt-dlp version: 2024.12.23
✅ FFmpeg version xxx
✅ دانلود موفق!
```

---

## 🛠️ راه‌حل‌های رایج

### مشکل 1: yt-dlp نصب نیست

**علامت:**
```
❌ خطا در SoundCloud: [Errno 2] No such file or directory: 'yt-dlp'
```

**راه‌حل:**
```bash
# در Dockerfile مطمئن شو این خط هست:
RUN pip install --no-cache-dir -U yt-dlp

# و این هم:
RUN yt-dlp --version
```

---

### مشکل 2: FFmpeg نصب نیست

**علامت:**
```
ERROR: ffmpeg not found
```

**راه‌حل:**
```dockerfile
# در Dockerfile
RUN apt-get install -y ffmpeg
```

---

### مشکل 3: Timeout میشه

**علامت:**
```
⏱️ YouTube timeout برای 'xxx'
```

**راه‌حل:**

در `services/downloader.py`:
```python
# افزایش timeout
stdout, stderr = await asyncio.wait_for(
    process.communicate(),
    timeout=90  # به جای 60
)
```

---

### مشکل 4: سرعت اینترنت کنده

**راه‌حل:**

استفاده از Spotify Preview فقط:

در `services/music_sender.py`:
```python
# خط ~65
download_file = False  # موقتاً غیرفعال کن
```

یا اینکه در `/menu` دکمه‌ای بزار که کاربر انتخاب کنه "با فایل" یا "بدون فایل".

---

## 📊 تست کامل

### تست 1: دستی در Terminal

```bash
# تست YouTube
yt-dlp "ytsearch1:The Weeknd Blinding Lights" \
  --extract-audio \
  --audio-format mp3 \
  -o "test.mp3"

# تست SoundCloud
yt-dlp "scsearch1:The Weeknd Blinding Lights" \
  --extract-audio \
  --audio-format mp3 \
  -o "test_sc.mp3"
```

### تست 2: از داخل Python

```python
import asyncio
from services.downloader import download_track_safe_async

async def test():
    result = await download_track_safe_async(
        "Blinding Lights",
        "The Weeknd"
    )
    print(f"Result: {result}")

asyncio.run(test())
```

### تست 3: از داخل ربات

```
/menu → موزیک تصادفی حالا
```

باید فایل MP3 بیاد، نه فقط لینک.

---

## 🔍 دیباگ پیشرفته

### نگاه کردن به لاگ‌های کامل

```bash
# در Render
tail -f /var/log/render.log

# یا اگه local هست
tail -f bot.log | grep -i "download\|youtube\|soundcloud"
```

### چک کردن فضای دیسک

```bash
df -h /app/downloads
```

اگه پُر بود:
```python
# cleanup_old_files رو کال کن
music_downloader.cleanup_old_files(max_age_hours=1)
```

---

## 💡 نکات مهم

1. **Render Free Plan محدودیت داره:**
   - CPU: 0.5 CPU
   - RAM: 512MB
   - ممکنه دانلود کند باشه یا timeout بخوره

2. **YouTube گاهی IP رو block می‌کنه:**
   - از SoundCloud استفاده کن
   - یا Proxy اضافه کن

3. **فضای دیسک محدوده:**
   - فایل‌های قدیمی رو پاک کن
   - از cleanup منظم استفاده کن

---

## 🚨 اگه همه چی شکست خورد

### Plan B: فقط Preview

در `core/config.py`:
```python
# اضافه کن
DOWNLOAD_ENABLED = False
```

در `services/music_sender.py`:
```python
from core.config import config

download_file = config.DOWNLOAD_ENABLED if hasattr(config, 'DOWNLOAD_ENABLED') else True
```

### Plan C: External Download Service

استفاده از سرویس external برای دانلود (خارج از scope این پروژه).

---

## 📞 گزارش مشکل

اگه مشکل حل نشد، این اطلاعات رو بده:

```bash
# 1. لاگ کامل (100 خط آخر)
tail -100 bot.log > debug_log.txt

# 2. نسخه‌ها
python --version
pip freeze > versions.txt

# 3. تست yt-dlp
yt-dlp --version > ytdlp_info.txt

# 4. محیط
echo "OS: $(uname -a)" > env_info.txt
echo "Disk: $(df -h /app)" >> env_info.txt
```

---

**آخرین بروزرسانی:** دسامبر 2024