"""
Music Sender - ارسال موزیک به کاربر یا کانال
"""
import logging
from typing import Optional
from telegram import Bot, InputMediaAudio
from telegram.error import TelegramError
from telegram.constants import ParseMode

from core.database import SessionLocal, SentTrack
from services.spotify import spotify_service, get_random_track_for_user
from services.musixmatch import get_track_lyrics  # همون helper جدید
from services.downloader import download_track_safe

logger = logging.getLogger(__name__)


# ==================== فرمت کردن پیام ====================

def format_track_message(
    track_info: dict,
    lyrics: Optional[str] = None,
    include_links: bool = True
) -> str:
    """
    فرمت کردن پیام موزیک برای ارسال
    
    Args:
        track_info: اطلاعات فرمت شده آهنگ از Spotify
        lyrics: متن آهنگ (اختیاری)
        include_links: نمایش لینک‌ها
    
    Returns:
        متن فرمت شده
    """
    # اطلاعات اصلی
    message = f"🎵 <b>{track_info['name']}</b>\n"
    message += f"🎤 {track_info['artist_str']}\n"
    message += f"💿 {track_info['album']}\n"
    message += f"⏱ {track_info['duration']}\n"
    
    # محبوبیت
    popularity = track_info.get('popularity', 0)
    if popularity:
        stars = '⭐' * (popularity // 20)
        message += f"📊 محبوبیت: {stars} ({popularity}/100)\n"
    
    # تاریخ انتشار
    if track_info.get('release_date'):
        message += f"📅 {track_info['release_date']}\n"
    
    message += "\n"
    
    # لینک‌ها
    if include_links:
        links = track_info.get('links', {})
        
        if links.get('spotify'):
            message += f"🎧 <a href='{links['spotify']}'>گوش کن در Spotify</a>\n"
        
        if links.get('preview'):
            message += f"▶️ <a href='{links['preview']}'>پیش‌نمایش 30 ثانیه</a>\n"
        
        message += "\n"
    
    # متن آهنگ (snippet)
    if lyrics:
        # فقط 4 خط اول
        lyrics_lines = lyrics.split('\n')[:4]
        lyrics_snippet = '\n'.join(lyrics_lines)
        
        message += f"📝 <b>متن آهنگ:</b>\n"
        message += f"<i>{lyrics_snippet}</i>\n"
        
        if len(lyrics.split('\n')) > 4:
            message += "<i>...</i>\n"
    
    return message.strip()


# ==================== ارسال روزانه ====================

async def send_daily_music_to_all():
    """
    ارسال روزانه موزیک به تمام کاربران فعال
    """
    db = SessionLocal()
    try:
        from core.database import User, UserSettings, UserGenre
        
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            settings = user.settings
            if not settings:
                continue
            
            genres = [g.genre for g in user.genres]
            if not genres:
                continue
            
            # انتخاب ژانر تصادفی اگر چندتا باشه
            genre = random.choice(genres)
            
            # ارسال
            await send_music_to_user(
                bot=None,  # باید bot رو از scheduler بگیری
                user_id=user.user_id,
                genre=genre,
                send_to=settings.send_to,
                channel_id=settings.channel_id
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در ارسال روزانه: {e}")
    finally:
        db.close()


# ==================== ارسال به کاربر ====================

async def send_music_to_user(
    bot: Bot,
    user_id: int,
    genre: str,
    send_to: str = 'private',
    channel_id: Optional[str] = None,
    download_file: bool = True
) -> bool:
    """
    ارسال یک موزیک به کاربر یا کانال
    
    Args:
        bot: نمونه Bot تلگرام
        user_id: شناسه کاربر
        genre: ژانر موزیک
        send_to: 'private' یا 'channel'
        channel_id: آیدی کانال اگر send_to=channel
        download_file: آیا فایل کامل دانلود بشه یا نه
    
    Returns:
        True اگر موفق، False اگر خطا
    """
    try:
        # گرفتن آهنگ تصادفی
        track_info = get_random_track_for_user(user_id, genre)
        if not track_info:
            await bot.send_message(
                chat_id=user_id,
                text="❌ نتونستم آهنگ مناسبی پیدا کنم! بعداً امتحان کن."
            )
            return False
        
        # گرفتن متن آهنگ
        lyrics = get_track_lyrics(track_info['name'], track_info['artist_str'])
        
        # دانلود فایل اگر لازم
        audio = None
        if download_file:
            file_path = download_track_safe(track_info['name'], track_info['artist_str'])
            if file_path:
                audio = open(file_path, 'rb')
        
        # فرمت پیام
        message_text = format_track_message(track_info, lyrics)
        
        # تعیین chat_id
        target_chat = channel_id if send_to == 'channel' else user_id
        
        # ارسال
        if audio:
            await bot.send_audio(
                chat_id=target_chat,
                audio=audio,
                caption=message_text,
                parse_mode=ParseMode.HTML,
                title=track_info['name'],
                performer=track_info['artist_str']
            )
            audio.close()
            if file_path:
                os.remove(file_path)  # پاک کردن فایل موقت
        else:
            await bot.send_message(
                chat_id=target_chat,
                text=message_text,
                parse_mode=ParseMode.HTML
            )
        
        # ذخیره در تاریخچه
        save_to_history(user_id, track_info)
        
        return True
        
    except TelegramError as e:
        logger.error(f"❌ خطای تلگرام در ارسال: {e}")
        
        # اگه مشکل دسترسی به کانال بود، به کاربر اطلاع بده
        if send_to == 'channel':
            await bot.send_message(
                chat_id=user_id,
                text=f"❌ نتونستم به کانال {channel_id} ارسال کنم!\n\n"
                     f"لطفاً مطمئن شو که:\n"
                     f"• من ادمین کانالم\n"
                     f"• شناسه کانال درسته\n\n"
                     f"برای تغییر تنظیمات از /menu استفاده کن."
            )
        
        return False
        
    except Exception as e:
        logger.error(f"❌ خطای کلی در ارسال موزیک: {e}")
        
        try:
            await bot.send_message(
                chat_id=user_id,
                text="❌ متأسفانه یه مشکلی پیش اومد!\n\n"
                     "لطفاً بعداً دوباره امتحان کن."
            )
        except:
            pass
        
        return False


def save_to_history(user_id: int, track_info: dict):
    """
    ذخیره آهنگ در تاریخچه
    
    Args:
        user_id: شناسه کاربر
        track_info: اطلاعات آهنگ
    """
    db = SessionLocal()
    try:
        sent_track = SentTrack(
            user_id=user_id,
            track_id=track_info['id'],
            track_name=track_info['name'],
            artist=track_info['artist_str']
        )
        
        db.add(sent_track)
        db.commit()
        
        logger.info(f"✅ آهنگ در تاریخچه کاربر {user_id} ذخیره شد")
        
    except Exception as e:
        logger.error(f"❌ خطا در ذخیره تاریخچه: {e}")
        db.rollback()
    finally:
        db.close()


# ==================== ارسال تست ====================

async def send_test_music(bot: Bot, user_id: int, genre: str = 'pop'):
    """
    ارسال تستی یک موزیک
    
    Args:
        bot: نمونه Bot
        user_id: شناسه کاربر
        genre: ژانر (پیش‌فرض: pop)
    """
    await send_music_to_user(
        bot=bot,
        user_id=user_id,
        genre=genre,
        send_to='private',
        download_file=True
    )