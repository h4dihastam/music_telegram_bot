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
from services.musixmatch import get_track_lyrics
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
        
        message += "\n"
    
    # پاورقی
    message += "━━━━━━━━━━━━━━━━\n"
    message += "🤖 ارسال شده توسط ربات موزیک\n"
    message += "#موزیک_روزانه"
    
    return message


def format_lyrics_full(track_info: dict, lyrics: str) -> str:
    """
    فرمت کردن متن کامل آهنگ برای ارسال جداگانه
    
    Args:
        track_info: اطلاعات آهنگ
        lyrics: متن کامل آهنگ
    
    Returns:
        متن فرمت شده
    """
    message = f"📝 <b>متن کامل آهنگ</b>\n\n"
    message += f"🎵 <b>{track_info['name']}</b>\n"
    message += f"🎤 {track_info['artist_str']}\n\n"
    message += "━━━━━━━━━━━━━━━━\n\n"
    message += f"{lyrics}\n\n"
    message += "━━━━━━━━━━━━━━━━\n"
    
    return message


# ==================== ارسال موزیک ====================

async def send_music_to_user(
    bot: Bot,
    user_id: int,
    genre: str,
    send_to: str = 'private',
    channel_id: Optional[str] = None,
    download_file: bool = True
) -> bool:
    """
    ارسال موزیک به کاربر یا کانال
    
    Args:
        bot: نمونه Bot تلگرام
        user_id: شناسه کاربر تلگرام
        genre: ژانر موزیک
        send_to: مقصد ارسال (private یا channel)
        channel_id: شناسه کانال (اگه send_to=channel)
        download_file: دانلود و ارسال فایل؟
    
    Returns:
        True اگه موفق بود
    """
    try:
        logger.info(f"🎵 شروع ارسال موزیک برای کاربر {user_id} (ژانر: {genre})")
        
        # 1. پیدا کردن آهنگ تصادفی
        track_info = get_random_track_for_user(user_id, genre)
        
        if not track_info:
            logger.error("❌ آهنگی پیدا نشد")
            await bot.send_message(
                chat_id=user_id,
                text="❌ متأسفانه آهنگ جدیدی پیدا نکردم!\n\n"
                     "لطفاً بعداً دوباره امتحان کن."
            )
            return False
        
        logger.info(f"✅ آهنگ انتخاب شد: {track_info['name']} - {track_info['artist_str']}")
        
        # 2. گرفتن متن آهنگ
        lyrics = None
        try:
            lyrics = get_track_lyrics(
                track_info['name'],
                track_info['artist_str'],
                track_info['id'],
                use_cache=True
            )
            if lyrics:
                logger.info(f"✅ متن آهنگ دریافت شد ({len(lyrics)} کاراکتر)")
        except Exception as e:
            logger.warning(f"⚠️ خطا در دریافت متن: {e}")
        
        # 3. دانلود فایل (اختیاری)
        audio_file = None
        if download_file:
            try:
                logger.info("📥 شروع دانلود فایل...")
                audio_file = download_track_safe(
                    track_info['name'],
                    track_info['artist_str'],
                    track_info
                )
                
                if audio_file:
                    logger.info(f"✅ فایل دانلود شد: {audio_file}")
                else:
                    logger.warning("⚠️ دانلود فایل ناموفق - فقط لینک ارسال می‌شه")
                    
            except Exception as e:
                logger.error(f"❌ خطا در دانلود: {e}")
        
        # 4. فرمت کردن پیام
        message = format_track_message(track_info, lyrics, include_links=True)
        
        # 5. تعیین مقصد ارسال
        target_chat = channel_id if send_to == 'channel' and channel_id else user_id
        
        # 6. ارسال
        try:
            if audio_file:
                # ارسال با فایل صوتی
                with open(audio_file, 'rb') as audio:
                    await bot.send_audio(
                        chat_id=target_chat,
                        audio=audio,
                        caption=message,
                        parse_mode=ParseMode.HTML,
                        title=track_info['name'],
                        performer=track_info['artist_str'],
                        duration=track_info['duration_ms'] // 1000,
                        thumb=track_info.get('cover_image')  # تصویر کاور
                    )
                
                logger.info(f"✅ موزیک با فایل به {target_chat} ارسال شد")
                
                # حذف فایل بعد از ارسال
                try:
                    import os
                    os.remove(audio_file)
                    logger.info(f"🗑️ فایل حذف شد: {audio_file}")
                except:
                    pass
                
            else:
                # ارسال بدون فایل (فقط لینک و اطلاعات)
                # اگه تصویر کاور داشتیم، با عکس بفرست
                if track_info.get('cover_image'):
                    await bot.send_photo(
                        chat_id=target_chat,
                        photo=track_info['cover_image'],
                        caption=message,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await bot.send_message(
                        chat_id=target_chat,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=False
                    )
                
                logger.info(f"✅ اطلاعات موزیک به {target_chat} ارسال شد")
            
            # 7. ارسال متن کامل آهنگ (اگه موجود بود)
            if lyrics and len(lyrics) > 200:
                lyrics_message = format_lyrics_full(track_info, lyrics)
                
                # بررسی طول پیام (حداکثر 4096 کاراکتر)
                if len(lyrics_message) > 4000:
                    # تقسیم به چند پیام
                    parts = [lyrics_message[i:i+4000] for i in range(0, len(lyrics_message), 4000)]
                    for part in parts:
                        await bot.send_message(
                            chat_id=target_chat,
                            text=part,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    await bot.send_message(
                        chat_id=target_chat,
                        text=lyrics_message,
                        parse_mode=ParseMode.HTML
                    )
                
                logger.info("✅ متن کامل آهنگ ارسال شد")
            
            # 8. ذخیره در تاریخچه
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