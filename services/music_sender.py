"""
Music Sender - ارسال موزیک (Fixed with async downloader)
"""
import logging
import os
from html import escape
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode

from core.database import SessionLocal, SentTrack
from services.spotify import get_random_track_for_user
from services.musixmatch import get_track_lyrics
from services.downloader import download_track_safe_async  # ✅ تغییر به async

logger = logging.getLogger(__name__)


def format_track_message(
    track_info: dict, 
    lyrics: Optional[str] = None
) -> str:
    """فرمت کردن پیام"""
    track_name = escape(str(track_info.get('name', 'Unknown')))
    artist_name = escape(str(track_info.get('artist_str', 'Unknown')))
    album_name = escape(str(track_info.get('album', 'Unknown')))
    duration = escape(str(track_info.get('duration', '-')))

    message = f"🎵 <b>{track_name}</b>\n"
    message += f"🎤 {artist_name}\n"
    message += f"💿 {album_name}\n"
    message += f"⏱ {duration}\n\n"
    
    # لینک‌ها
    links = track_info.get('links', {})
    if links.get('spotify'):
        spotify_url = escape(str(links['spotify']), quote=True)
        message += f"🎧 <a href=\"{spotify_url}\">Spotify</a>"
    
    if links.get('preview'):
        preview_url = escape(str(links['preview']), quote=True)
        message += f" | <a href=\"{preview_url}\">Preview</a>"
    
    message += "\n"
    
    # متن آهنگ
    if lyrics:
        from services.musixmatch import lyrics_service
        formatted_lyrics = lyrics_service.format_lyrics_for_telegram(lyrics)
        if formatted_lyrics:
            message += f"\n📝 متن آهنگ:\n<i>{formatted_lyrics}</i>"
    
    return message.strip()


async def send_music_to_user(
    bot: Bot,
    user_id: int,
    genre: str,
    send_to: str = 'private',
    channel_id: Optional[str] = None,
    download_file: bool = True
) -> bool:
    """ارسال موزیک به کاربر"""
    
    try:
        # دریافت آهنگ
        logger.info(f"🎵 دریافت آهنگ برای کاربر {user_id}, ژانر: {genre}")
        track_info = get_random_track_for_user(user_id, genre)
        
        if not track_info:
            logger.warning("❌ آهنگ پیدا نشد")
            await bot.send_message(
                chat_id=user_id,
                text="❌ متأسفانه نتونستم آهنگ مناسبی پیدا کنم!\n\n"
                     "لطفاً بعداً دوباره امتحان کن."
            )
            return False
        
        logger.info(f"✅ آهنگ پیدا شد: {track_info['name']} - {track_info['artist_str']}")
        
        # دریافت متن
        lyrics = None
        try:
            lyrics = get_track_lyrics(
                track_info['name'], 
                track_info['artist_str']
            )
            if lyrics:
                logger.info("✅ متن آهنگ دریافت شد")
        except Exception as e:
            logger.warning(f"⚠️ خطا در دریافت متن: {e}")
        
        # فرمت پیام
        message_text = format_track_message(track_info, lyrics)
        
        # تعیین مقصد
        target_chat = channel_id if send_to == 'channel' else user_id
        
        # دانلود فایل
        file_path = None
        if download_file:
            try:
                logger.info("📥 شروع دانلود فایل...")
                # ✅ تغییر به await
                file_path = await download_track_safe_async(
                    track_name=track_info['name'],
                    artist_name=track_info['artist_str'],
                    spotify_url=track_info['links'].get('spotify'),
                    preview_url=track_info['links'].get('preview')
                )
                
                if file_path:
                    logger.info(f"✅ فایل دانلود شد: {file_path}")
            except Exception as e:
                logger.error(f"❌ خطا در دانلود: {e}")
        
        # ارسال
        if file_path and os.path.exists(file_path):
            logger.info("📤 ارسال فایل صوتی...")
            try:
                with open(file_path, 'rb') as audio_file:
                    await bot.send_audio(
                        chat_id=target_chat,
                        audio=audio_file,
                        caption=message_text,
                        parse_mode=ParseMode.HTML,
                        title=track_info['name'],
                        performer=track_info['artist_str'],
                        duration=int(track_info.get('duration_ms', 0) / 1000) if 'duration_ms' in track_info else None
                    )
                logger.info("✅ فایل ارسال شد")
                
                # پاک کردن فایل
                try:
                    os.remove(file_path)
                    logger.info("🗑️ فایل پاک شد")
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"❌ خطا در ارسال فایل: {e}")
                # ارسال فقط متن
                await bot.send_message(
                    chat_id=target_chat,
                    text=message_text + "\n\n⚠️ فایل در دسترس نبود",
                    parse_mode=ParseMode.HTML
                )
        else:
            # ارسال فقط اطلاعات
            logger.info("📤 ارسال اطلاعات (بدون فایل)...")
            await bot.send_message(
                chat_id=target_chat,
                text=message_text + "\n\n💡 از لینک Spotify گوش کن!",
                parse_mode=ParseMode.HTML
            )
        
        # ذخیره در تاریخچه
        db = SessionLocal()
        try:
            db.add(SentTrack(
                user_id=user_id,
                track_id=track_info['id'],
                track_name=track_info['name'],
                artist=track_info['artist_str']
            ))
            db.commit()
            logger.info("✅ در تاریخچه ذخیره شد")
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطای کلی در ارسال: {e}", exc_info=True)
        try:
            await bot.send_message(
                chat_id=user_id,
                text="❌ متأسفانه مشکلی پیش اومد!\n\n"
                     "لطفاً بعداً دوباره امتحان کن."
            )
        except:
            pass
        return False


async def send_random_music_now(bot: Bot, user_id: int):
    """ارسال موزیک تصادفی الان"""
    db = SessionLocal()
    try:
        from core.database import UserGenre
        import random
        
        genres = db.query(UserGenre).filter(
            UserGenre.user_id == user_id
        ).all()
        
        if not genres:
            await bot.send_message(
                chat_id=user_id,
                text="❌ هنوز ژانری انتخاب نکردی!\n\n"
                     "/start بزن تا شروع کنیم."
            )
            return
        
        genre = random.choice([g.genre for g in genres])
        
        await bot.send_message(
            chat_id=user_id,
            text="🎵 در حال پیدا کردن آهنگ...\n⏳ لحظه‌ای صبر کن..."
        )
        
        await send_music_to_user(
            bot=bot,
            user_id=user_id,
            genre=genre,
            send_to='private',
            download_file=True
        )
        
    finally:
        db.close()
