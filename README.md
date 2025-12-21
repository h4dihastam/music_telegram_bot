# 🎵 Music Telegram Bot

ربات تلگرام برای ارسال خودکار موزیک روزانه بر اساس سلیقه کاربر

## ✨ ویژگی‌ها

- 🎵 انتخاب ژانر موسیقی مورد علاقه
- ⏰ ارسال خودکار روزانه در زمان دلخواه
- 📍 ارسال به پیوی یا کانال تلگرام
- 🎧 دریافت لینک Spotify و اطلاعات آهنگ
- 📝 نمایش متن آهنگ (اگه موجود باشه)
- 📥 دانلود فایل MP3 (اختیاری)

## 🚀 نصب و راه‌اندازی

### پیش‌نیازها

- Python 3.11+
- FFmpeg (برای دانلود موزیک)

### نصب Local

```bash
# کلون کردن پروژه
git clone https://github.com/your-username/music-telegram-bot.git
cd music-telegram-bot

# ساخت محیط مجازی
python -m venv venv
source venv/bin/activate  # در Windows: venv\Scripts\activate

# نصب dependencies
pip install -r requirements.txt

# ساخت فایل .env
cp .env.example .env
# ویرایش .env و اضافه کردن توکن‌ها
```

### تنظیم `.env`

```env
BOT_TOKEN=توکن_ربات_از_BotFather
SPOTIFY_CLIENT_ID=از_developer.spotify.com
SPOTIFY_CLIENT_SECRET=از_developer.spotify.com
MUSIXMATCH_API_KEY=اختیاری
DATABASE_URL=sqlite:///music_bot.db
```

### اجرا

```bash
python main.py
```

## 🌐 Deploy در Render

### روش 1: با GitHub (پیشنهادی)

1. پوش کردن کد به GitHub
2. رفتن به [Render.com](https://render.com)
3. New → Web Service
4. Connect GitHub repository
5. تنظیمات:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
6. اضافه کردن Environment Variables:
   - `BOT_TOKEN`
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
   - `PORT=8080`
7. Deploy!

### روش 2: با Docker

```bash
# ساخت image
docker build -t music-telegram-bot .

# اجرا
docker run -d \
  -e BOT_TOKEN=your_token \
  -e SPOTIFY_CLIENT_ID=your_id \
  -e SPOTIFY_CLIENT_SECRET=your_secret \
  music-telegram-bot
```

## 📋 دستورات ربات

- `/start` - شروع و تنظیمات اولیه
- `/menu` - نمایش منوی اصلی
- `/status` - نمایش وضعیت فعلی
- `/help` - راهنما

## 🎯 نحوه استفاده

1. `/start` را بزنید
2. ژانر موسیقی مورد علاقه خود را انتخاب کنید
3. زمان ارسال روزانه را تنظیم کنید
4. مقصد ارسال (پیوی یا کانال) را انتخاب کنید
5. اگر کانال انتخاب کردید، آیدی کانال را وارد کنید
6. تمام! هر روز یک آهنگ جدید دریافت می‌کنید 🎶

## 🔧 تنظیمات پیشرفته

### افزودن ژانر جدید

فایل `data/genres.json` را ویرایش کنید:

```json
{
  "id": "genre_id",
  "name": "نام فارسی ژانر"
}
```

### تغییر منطقه زمانی

در `.env`:

```env
DEFAULT_TIMEZONE=Asia/Tehran
```

## 🛠️ ساختار پروژه

```
music_telegram_bot/
├── bot/
│   ├── handlers/      # هندلرهای تلگرام
│   └── keyboards/     # کیبوردهای inline
├── core/
│   ├── config.py      # تنظیمات
│   ├── database.py    # مدل‌های دیتابیس
│   └── scheduler.py   # زمان‌بندی ارسال
├── services/
│   ├── spotify.py     # سرویس Spotify
│   ├── musixmatch.py  # سرویس Musixmatch
│   ├── downloader.py  # دانلود موزیک
│   └── music_sender.py # ارسال موزیک
├── data/
│   └── genres.json    # لیست ژانرها
└── main.py            # نقطه ورود
```

## 📝 لایسنس

MIT License

## 🤝 مشارکت

Pull Request ها خوش‌آمدید!

## 📧 تماس

برای هر سوال یا مشکلی، Issue باز کنید.

---

**⚠️ توجه**: این پروژه برای اهداف آموزشی است. لطفاً قوانین کپی‌رایت موزیک را رعایت کنید.