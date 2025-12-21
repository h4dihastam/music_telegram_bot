"""
Music Sender - ارسال موزیک به کاربر یا کانال (اصلاح‌شده با error handling بهتر)
"""
import logging
import os
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode

from core.database import SessionLocal, SentTrack
from services.spotify import spotify_service, get_random_track_for_user
from services.musixmatch import get_track_lyrics
from services.downloader import download_track_safe

logger = logging.getLogger(__name__)

def format_track_message(track_info: dict, lyrics: Optional[str] = None) -> str:
    message = f"🎵 <b>{track_info['name']}</b>\n"
    message += f"🎤 {track_info['artist_str']}\n"
    message += f"💿 {track_info['album']}\n"
    message += f"⏱ {track_info['duration']}\n\n"
    
    links = track_info.get('links', {})
    if links.get('spotify'):
        message += f"🎧 <a href='{links['spotify']}'>گوش کن در Spotify</a>\n"
    if links.get('preview'):
        message += f"▶️ <a href='{links['preview']}'>پیش‌نمایش 30 ثانیه</a>\n\n"
    
    if lyrics:
        lyrics_snippet = '\n'.join(lyrics.split('\n')[:4])
        message += f"📝 متن آهنگ:\n<i>{lyrics_snippet}</i>\n"
        if len(lyrics.split('\n')) > 4:
            message += "<i>...</i>"
    
    return message.strip()

async def send_music_to_user(
    bot: Bot,
    user_id: int,
    genre: str,
    send_to: str = 'private',
    channel_id: Optional[str] = None,
    download_file: bool = True
) -> bool:
    try:
        track_info = get_random_track_for_user(user_id, genre)
        if not track_info:
            await bot.send_message(chat_id=user_id, text="❌ نتونستم آهنگ مناسبی پیدا کنم! بعداً دوباره امتحان کن.")
            return False
        
        lyrics = get_track_lyrics(track_info['name'], track_info['artist_str'])
        
        message_text = format_track_message(track_info, lyrics)
        
        target_chat = channel_id if send_to == 'channel' else user_id
        
        file_path = None
        if download_file:
            file_path = download_track_safe(track_info['name'], track_info['artist_str'])
        
        if file_path and os.path.exists(file_path):
            await bot.send_audio(
                chat_id=target_chat,
                audio=open(file_path, 'rb'),
                caption=message_text,
                parse_mode=ParseMode.HTML,
                title=track_info['name'],
                performer=track_info['artist_str']
            )
            os.remove(file_path)
        else:
            await bot.send_message(
                chat_id=target_chat,
                text=message_text + "\n\n⚠️ فایل کامل در دسترس نبود، لینک‌ها رو چک کن!",
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
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        logger.error(f"خطا در ارسال موزیک تصادفی: {e}")
        await bot.send_message(chat_id=user_id, text="❌ نتونستم آهنگ بفرستم! لطفاً بعداً امتحان کن.")
        return False

# برای دکمه "موزیک تصادفی حالا"
async def send_random_music_now(bot: Bot, user_id: int):
    db = SessionLocal()
    try:
        from core.database import UserGenre
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        if not genres:
            await bot.send_message(chat_id=user_id, text="❌ هنوز ژانری انتخاب نکردی! /start بزن.")
            return
        
        genre = genres[0].genre  # یا random.choice اگر چندتا باشه
        await send_music_to_user(bot=bot, user_id=user_id, genre=genre, send_to='private')
    finally:
        db.close()