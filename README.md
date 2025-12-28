# 🎵 ربات موزیک تلگرام

ربات تلگرام هوشمند برای ارسال خودکار موزیک روزانه بر اساس سلیقه کاربر

## ✨ ویژگی‌ها

- 🎵 **انتخاب چندگانه ژانر** - پاپ، راک، الکترونیک، **ایرانی** و 15+ ژانر دیگر
- ⏰ **ارسال خودکار روزانه** - در زمان دلخواه شما
- 📍 **ارسال به پیوی یا کانال** - انعطاف کامل
- 🎧 **دانلود از چند منبع** - SoundCloud (اولویت)، YouTube، Spotify
- 📝 **نمایش متن آهنگ** - با API چندگانه
- 🇮🇷 **پشتیبانی کامل فارسی** - موزیک ایرانی، ترکی، عربی
- 💾 **دیتای پایدار** - اطلاعات شما ذخیره می‌مونه

## 🚀 نصب سریع

### 1. کلون پروژه

```bash
git clone https://github.com/your-username/music-telegram-bot.git
cd music-telegram-bot
```

### 2. نصب Python Dependencies

```bash
# ساخت محیط مجازی
python -m venv venv

# فعال‌سازی
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# نصب
pip install -r requirements.txt
```

### 3. نصب FFmpeg (ضروری)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
- دانلود از [ffmpeg.org](https://ffmpeg.org/download.html)
- اضافه کردن به PATH

### 4. تنظیمات

```bash
# کپی فایل نمونه
cp .env.example .env

# ویرایش .env
nano .env  # یا هر ادیتور دیگر
```

**محتوای `.env`:**
```env
BOT_TOKEN=123456:ABC-DEF...           # از @BotFather
SPOTIFY_CLIENT_ID=your_id             # از developer.spotify.com
SPOTIFY_CLIENT_SECRET=your_secret     # از developer.spotify.com
DATABASE_URL=sqlite:///music_bot.db
DEFAULT_TIMEZONE=Asia/Tehran
PORT=8080
```

### 5. اجرا

```bash
python main.py
```

## 🔧 راهنمای دریافت API Keys

### Telegram Bot Token

1. پیام به [@BotFather](https://t.me/BotFather) در تلگرام
2. دستور `/newbot`
3. نام ربات را وارد کنید
4. توکن را کپی کنید

### Spotify API

1. [developer.spotify.com](https://developer.spotify.com/dashboard) باز کنید
2. "Create App" کلیک کنید
3. نام و توضیحات را پر کنید
4. `Client ID` و `Client Secret` را کپی کنید

## 🌐 Deploy در Render (رایگان!)

### گام 1: آماده‌سازی

```bash
# مطمئن شو که همه فایل‌ها commit شدن
git add .
git commit -m "Ready for deployment"
git push origin main
```

### گام 2: ساخت Service در Render

1. [render.com](https://render.com) باز کن
2. **New** → **Web Service**
3. Connect GitHub repository
4. تنظیمات:
   - **Name**: music-telegram-bot
   - **Environment**: Docker
   - **Plan**: Free

### گام 3: Environment Variables

در بخش **Environment** این متغیرها رو اضافه کن:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | توکن ربات از BotFather |
| `SPOTIFY_CLIENT_ID` | کلاینت آیدی Spotify |
| `SPOTIFY_CLIENT_SECRET` | سیکرت Spotify |
| `DATABASE_URL` | `sqlite:////app/data/music_bot.db` |
| `PORT` | `8080` |

### گام 4: Disk (مهم!)

در بخش **Disks**:
- **Name**: bot-persistent-data
- **Mount Path**: `/app/data`
- **Size**: 1 GB

> ⚠️ **نکته مهم**: بدون Disk، دیتای شما بعد از هر restart پاک میشه!

### گام 5: Deploy

کلیک **Create Web Service**. منتظر بمون تا build تموم شه (5-10 دقیقه).

## 📱 استفاده از ربات

### دستورات اصلی

- `/start` - شروع و تنظیمات اولیه
- `/menu` - منوی اصلی
- `/status` - نمایش وضعیت فعلی
- `/help` - راهنما

### راهنمای سریع

1. **شروع**: `/start` بزنید
2. **ژانر**: یک یا چند ژانر انتخاب کنید
3. **زمان**: زمان ارسال روزانه رو تنظیم کنید
4. **مقصد**: پیوی یا کانال؟
   - اگه کانال: ربات رو ادمین کنید و آیدی کانال رو بدید
5. **تمام!** هر روز موزیک دریافت می‌کنید 🎶

### نمونه استفاده برای کانال

```
1. ربات رو به کانال اضافه کنید
2. ربات رو ادمین کنید (با دسترسی ارسال پیام)
3. آیدی کانال رو پیدا کنید:
   - اگه username داره: @my_channel
   - اگه نداره: -1001234567890
4. در ربات گزینه "کانال" رو بزنید
5. آیدی رو بفرستید
```

## 🎵 ژانرهای موجود

- 🎸 پاپ، راک، متال، ایندی
- 🎤 هیپ‌هاپ، رپ، آر‌اند‌بی
- 🎹 الکترونیک، دنس، EDM
- 🎺 جاز، بلوز، کلاسیک
- 🌍 **ایرانی، ترکی، عربی، لاتین**
- 🇰🇷 کی‌پاپ
- 🪕 فولک، کانتری، رگه

## 🔍 نحوه دانلود موزیک

ربات از **3 منبع** به ترتیب تلاش می‌کنه:

1. **SoundCloud** (اولویت اول) - کیفیت عالی، کامل
2. **YouTube** - معمولاً موفق
3. **Spotify Preview** (آخرین راه) - فقط 30 ثانیه

## 🛠️ عیب‌یابی

### مشکل: "آهنگ پیدا نشد"

**راه‌حل:**
- Spotify API credentials رو چک کنید
- اینترنت سرور رو بررسی کنید
- لاگ‌ها رو چک کنید: `tail -f bot.log`

### مشکل: "دیتا پاک میشه"

**راه‌حل:**
- مطمئن شوید که در Render **Disk** تنظیم شده
- چک کنید که `DATABASE_URL` به `/app/data/` اشاره می‌کنه

### مشکل: "زمان ارسال کار نمی‌کنه"

**راه‌حل:**
- فرمت زمان رو چک کنید (HH:MM مثل 09:30)
- Timezone رو بررسی کنید
- لاگ scheduler رو ببینید

### مشکل: "دانلود نمی‌شه"

**راه‌حل:**
- FFmpeg نصب باشه: `ffmpeg -version`
- yt-dlp آپدیت باشه: `pip install -U yt-dlp`

## 📊 ساختار پروژه

```
music_telegram_bot/
├── bot/
│   ├── handlers/          # هندلرهای تلگرام
│   │   ├── start.py       # فرآیند Setup
│   │   ├── settings.py    # منو و تنظیمات
│   │   ├── genre.py       # انتخاب ژانر
│   │   └── channel.py     # تنظیمات کانال
│   ├── keyboards/         # کیبوردها
│   └── states.py          # State های conversation
├── core/
│   ├── config.py          # تنظیمات
│   ├── database.py        # مدل‌های دیتابیس
│   └── scheduler.py       # زمان‌بندی
├── services/
│   ├── spotify.py         # سرویس Spotify
│   ├── musixmatch.py      # متن آهنگ
│   ├── downloader.py      # دانلود موزیک
│   └── music_sender.py    # ارسال موزیک
├── data/
│   └── genres.json        # لیست ژانرها
├── utils/
│   ├── helpers.py         # توابع کمکی
│   └── decorators.py      # دکوراتورها
├── main.py                # نقطه ورود
├── Dockerfile             # برای Docker
├── render.yaml            # تنظیمات Render
└── requirements.txt       # Dependencies
```

## 🔒 امنیت

- **هیچ‌وقت** `.env` رو commit نکنید
- توکن‌ها رو فقط در Environment Variables ذخیره کنید
- در production از PostgreSQL استفاده کنید

## 🐛 گزارش مشکل

اگه مشکلی پیدا کردید:

1. لاگ‌ها رو چک کنید: `bot.log`
2. Issue باز کنید در GitHub
3. اطلاعات لازم رو بدید:
   - توضیح مشکل
   - لاگ‌های خطا
   - نسخه Python
   - محیط (Local/Render/Docker)

## 🤝 مشارکت

Pull Request ها خوش‌آمدید! برای تغییرات بزرگ، اول Issue باز کنید.

## 📝 لایسنس

MIT License - استفاده آزاد

## ⚠️ تذکر قانونی

این پروژه برای اهداف آموزشی است. لطفاً:
- قوانین کپی‌رایت موزیک را رعایت کنید
- از موزیک دانلود شده فقط برای استفاده شخصی استفاده کنید
- موزیک را بدون مجوز توزیع نکنید

## 💬 پشتیبانی

- 📧 ایمیل: your-email@example.com
- 💬 تلگرام: @your_username
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/music-telegram-bot/issues)

## 🎉 تشکر

از این پروژه‌ها الهام گرفته شده:
- python-telegram-bot
- spotipy
- yt-dlp

---

**ساخته شده با ❤️ برای عاشقان موزیک**

اگه خوشت اومد، یه ⭐ بده!