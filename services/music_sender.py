"""
Music Sender - با پشتیبانی از _needs_search و fix خطای like
"""
import logging
import os
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError, BadRequest
from telegram.constants import ParseMode

from core.database import SessionLocal, SentTrack
from services.spotify import get_random_track_for_user
from services.musixmatch import get_track_lyrics
from services.downloader import download_track_safe_async
from services.like_system import get_like_keyboard

logger = logging.getLogger(__name__)


def format_track_message(track_info: dict, lyrics: Optional[str] = None) -> str:
    message = f"🎵 <b>{track_info['name']}</b>\n"
    message += f"🎤 {track_info['artist_str']}\n"
    message += f"💿 {track_info['album']}\n"
    message += f"⏱ {track_info['duration']}\n\n"
    
    links = track_info.get('links', {})
    if links.get('spotify'):
        message += f"🎧 <a href='{links['spotify']}'>Spotify</a>"
    if links.get('preview'):
        message += f" | <a href='{links['preview']}'>Preview</a>"
    message += "\n"
    
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
    download_file: bool = True,
    track_info: Optional[dict] = None
) -> bool:
    
    try:
        if not track_info:
            logger.info(f"🎵 دریافت آهنگ برای کاربر {user_id}, ژانر: {genre}")
            track_info = get_random_track_for_user(user_id, genre)
        
        if not track_info:
            logger.warning("❌ آهنگ پیدا نشد")
            await bot.send_message(
                chat_id=user_id,
                text="❌ متأسفانه نتونستم آهنگ مناسبی پیدا کنم!\n\nلطفاً بعداً دوباره امتحان کن."
            )
            return False
        
        # اگه آهنگ از حالت fallback باشه (بدون نام)، نام هنرمند رو می‌ذاریم
        if track_info.get('_needs_search') and not track_info.get('name'):
            track_info['name'] = f"آهنگ از {track_info['artist_str']}"
        
        logger.info(f"✅ آهنگ: {track_info['name']} - {track_info['artist_str']}")
        
        # متن آهنگ
        lyrics = None
        try:
            if track_info.get('name') and not track_info.get('_needs_search'):
                lyrics = get_track_lyrics(track_info['name'], track_info['artist_str'])
        except Exception as e:
            logger.warning(f"⚠️ خطا در متن: {e}")
        
        message_text = format_track_message(track_info, lyrics)
        target_chat = channel_id if send_to == 'channel' else user_id
        
        reply_markup = None
        if send_to == 'private' and track_info.get('id'):
            reply_markup = get_like_keyboard(track_info['id'], user_id)
        
        # دانلود
        file_path = None
        if download_file:
            try:
                logger.info("📥 شروع دانلود فایل...")
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
                        reply_markup=reply_markup
                    )
                logger.info("✅ فایل ارسال شد")
                try:
                    os.remove(file_path)
                except:
                    pass
            except Exception as e:
                logger.error(f"❌ خطا در ارسال فایل: {e}")
                await bot.send_message(
                    chat_id=target_chat,
                    text=message_text + "\n\n⚠️ فایل در دسترس نبود",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
        else:
            logger.info("📤 ارسال بدون فایل...")
            await bot.send_message(
                chat_id=target_chat,
                text=message_text + "\n\n💡 از لینک Spotify گوش کن!",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
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
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطای کلی: {e}", exc_info=True)
        try:
            await bot.send_message(
                chat_id=user_id,
                text="❌ متأسفانه مشکلی پیش اومد!\n\nلطفاً بعداً دوباره امتحان کن."
            )
        except:
            pass
        return False


async def send_random_music_now(bot: Bot, user_id: int):
    from core.database import SessionLocal, UserGenre
    import random
    
    db = SessionLocal()
    try:
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        if not genres:
            await bot.send_message(
                chat_id=user_id,
                text="❌ هنوز ژانری انتخاب نکردی!\n\n/start بزن تا شروع کنیم."
            )
            return
        genre = random.choice([g.genre for g in genres])
    finally:
        db.close()
    
    await bot.send_message(chat_id=user_id, text="🎵 در حال پیدا کردن آهنگ...\n⏳ لحظه‌ای صبر کن...")
    await send_music_to_user(bot=bot, user_id=user_id, genre=genre, send_to='private', download_file=True)
