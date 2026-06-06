"""
Handler برای پردازش ورودی‌های مختلف کاربر
(ویس، ویدیو، لینک، متن)
"""
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from pathlib import Path

from services.music_recognition import recognition_service, recognize_music_from_instagram
from services.spotify import spotify_service
from services.music_sender import send_music_to_user
from core.database import SessionLocal, DownloadedTrack

logger = logging.getLogger(__name__)



async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشخیص آهنگ از فایل صوتی ارسال‌شده توسط کاربر."""
    if not recognition_service.is_available():
        await update.message.reply_text(
            "❌ متأسفانه سرویس تشخیص آهنگ در دسترس نیست!\n\n"
            "می‌تونی اسم آهنگ یا خواننده رو بفرستی."
        )
        return

    audio = update.message.audio or update.message.document
    if not audio:
        return

    if getattr(audio, 'file_size', 0) and audio.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ حجم فایل زیاد است! لطفاً یک نمونه کوتاه‌تر (حداکثر 20MB) بفرست.")
        return

    msg = await update.message.reply_text("🎧 در حال تشخیص آهنگ از فایل ارسالی...\n⏳ چند ثانیه صبر کن...")
    suffix = Path(getattr(audio, 'file_name', '') or 'sample.mp3').suffix or '.mp3'
    file_path = Path("temp") / f"audio_{update.effective_user.id}{suffix}"

    try:
        file = await context.bot.get_file(audio.file_id)
        await file.download_to_drive(file_path)
        result = await recognition_service.recognize_from_file(str(file_path))

        if result and result.get('title'):
            track_name = result['title']
            artist = ', '.join(result.get('artists', ['Unknown']))
            await msg.edit_text(
                f"✅ <b>آهنگ پیدا شد!</b> 🎉\n\n"
                f"🎵 {track_name}\n"
                f"🎤 {artist}\n\n"
                f"📥 در حال جستجو و ارسال...",
                parse_mode='HTML'
            )
            await search_and_send_track(update, context, track_name, artist, source='audio')
        else:
            await msg.edit_text(
                "😕 نتونستم آهنگ رو از فایل تشخیص بدم.\n\n"
                "یک نمونه واضح‌تر بفرست یا اسم آهنگ/خواننده رو مستقیم بنویس."
            )
    except Exception as e:
        logger.error(f"❌ خطا در تشخیص فایل صوتی: {e}", exc_info=True)
        await msg.edit_text("❌ مشکلی در پردازش فایل پیش اومد!")
    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass
        context.user_data.pop('waiting_for', None)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش ویس برای تشخیص آهنگ"""
    
    # چک کنیم که کاربر منتظر ویس هست
    if context.user_data.get('waiting_for') != 'voice_or_lyrics':
        return
    
    if not recognition_service.is_available():
        await update.message.reply_text(
            "❌ متأسفانه سرویس تشخیص آهنگ در دسترس نیست!\n\n"
            "لطفاً اسم آهنگ رو مستقیم بنویس."
        )
        return
    
    msg = await update.message.reply_text("🎤 در حال تشخیص آهنگ از ویس...\n⏳ چند ثانیه صبر کن...")
    
    try:
        # دانلود ویس
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        voice_path = temp_dir / f"voice_{update.effective_user.id}.ogg"
        
        await file.download_to_drive(voice_path)
        
        # تشخیص آهنگ
        result = await recognition_service.recognize_from_file(str(voice_path))
        
        # پاک کردن فایل
        try:
            os.remove(voice_path)
        except:
            pass
        
        if result and result.get('title'):
            # آهنگ پیدا شد!
            track_name = result['title']
            artist = ', '.join(result.get('artists', ['Unknown']))
            score = result.get('score', 0)
            
            await msg.edit_text(
                f"✅ <b>آهنگ پیدا شد!</b> 🎉\n\n"
                f"🎵 {track_name}\n"
                f"🎤 {artist}\n"
                f"🎯 اطمینان: {score}%\n\n"
                f"📥 در حال دانلود و ارسال...",
                parse_mode='HTML'
            )
            
            # جستجو در Spotify
            await search_and_send_track(
                update, context,
                track_name=track_name,
                artist=artist,
                source='voice'
            )
        else:
            await msg.edit_text(
                "😕 متأسفانه نتونستم آهنگ رو تشخیص بدم!\n\n"
                "می‌تونی:\n"
                "• یه ویس واضح‌تر بفرستی\n"
                "• اسم آهنگ رو بنویسی"
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در تشخیص ویس: {e}", exc_info=True)
        await msg.edit_text(
            "❌ مشکلی پیش اومد!\n\n"
            "لطفاً دوباره امتحان کن یا اسم آهنگ رو بنویس."
        )
    finally:
        context.user_data.pop('waiting_for', None)


async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش ویدیو برای تشخیص آهنگ"""
    
    # چک کنیم که کاربر منتظر ویدیو هست
    if context.user_data.get('waiting_for') != 'video_clip':
        return
    
    if not recognition_service.is_available():
        await update.message.reply_text(
            "❌ متأسفانه سرویس تشخیص آهنگ در دسترس نیست!"
        )
        return
    
    msg = await update.message.reply_text(
        "🎬 در حال پردازش ویدیو...\n⏳ ممکنه یکم طول بکشه..."
    )
    
    try:
        # دانلود ویدیو
        video = update.message.video
        
        # چک حجم (حداکثر 20MB)
        if video.file_size > 20 * 1024 * 1024:
            await msg.edit_text(
                "❌ حجم ویدیو زیاده! (حداکثر 20MB)\n\n"
                "یه ویدیو کوتاه‌تر بفرست."
            )
            return
        
        file = await context.bot.get_file(video.file_id)
        
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        video_path = temp_dir / f"video_{update.effective_user.id}.mp4"
        
        await file.download_to_drive(video_path)
        
        # استخراج صدا
        audio_path = await recognition_service.extract_audio_from_video(str(video_path))
        
        if not audio_path:
            await msg.edit_text("❌ نتونستم صدای ویدیو رو استخراج کنم!")
            return
        
        # تشخیص آهنگ
        result = await recognition_service.recognize_from_file(audio_path)
        
        # پاک‌سازی
        try:
            os.remove(video_path)
            os.remove(audio_path)
        except:
            pass
        
        if result and result.get('title'):
            track_name = result['title']
            artist = ', '.join(result.get('artists', ['Unknown']))
            
            await msg.edit_text(
                f"✅ <b>آهنگ داخل ویدیو پیدا شد!</b> 🎉\n\n"
                f"🎵 {track_name}\n"
                f"🎤 {artist}\n\n"
                f"📥 در حال ارسال...",
                parse_mode='HTML'
            )
            
            await search_and_send_track(
                update, context,
                track_name=track_name,
                artist=artist,
                source='video'
            )
        else:
            await msg.edit_text(
                "😕 متأسفانه نتونستم آهنگ رو تشخیص بدم!\n\n"
                "احتملاً:\n"
                "• آهنگ خیلی آروم بوده\n"
                "• صدای اطراف زیاد بوده\n"
                "• آهنگ ناشناس بوده"
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در تشخیص ویدیو: {e}", exc_info=True)
        await msg.edit_text("❌ مشکلی پیش اومد! دوباره امتحان کن.")
    finally:
        context.user_data.pop('waiting_for', None)


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش ورودی متنی (لینک یا اسم آهنگ)"""
    
    text = update.message.text.strip()
    waiting_for = context.user_data.get('waiting_for')
    
    if not waiting_for:
        return
    
    # لینک اینستاگرام
    if waiting_for == 'instagram_link':
        await handle_instagram_link(update, context, text)
    
    # اسم آهنگ
    elif waiting_for == 'track_name':
        await handle_track_search(update, context, text)
    
    # متن آهنگ (lyrics)
    elif waiting_for == 'voice_or_lyrics':
        await handle_lyrics_search(update, context, text)


async def handle_instagram_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """پردازش لینک اینستاگرام"""
    
    # بررسی فرمت لینک
    if not re.match(r'https?://(www\.)?(instagram\.com|instagr\.am)/', url):
        await update.message.reply_text(
            "❌ لینک اینستاگرام معتبر نیست!\n\n"
            "مثال درست:\n"
            "<code>https://www.instagram.com/p/ABC123/</code>",
            parse_mode='HTML'
        )
        return
    
    if not recognition_service.is_available():
        await update.message.reply_text(
            "❌ متأسفانه سرویس تشخیص آهنگ در دسترس نیست!"
        )
        context.user_data.pop('waiting_for', None)
        return
    
    msg = await update.message.reply_text(
        "📱 در حال دانلود از اینستاگرام...\n⏳ ممکنه یکم طول بکشه..."
    )
    
    try:
        # تشخیص آهنگ از لینک
        result = await recognize_music_from_instagram(url)
        
        if result and result.get('title'):
            track_name = result['title']
            artist = ', '.join(result.get('artists', ['Unknown']))
            
            await msg.edit_text(
                f"✅ <b>آهنگ داخل ویدیو پیدا شد!</b> 🎉\n\n"
                f"🎵 {track_name}\n"
                f"🎤 {artist}\n\n"
                f"📥 در حال ارسال...",
                parse_mode='HTML'
            )
            
            await search_and_send_track(
                update, context,
                track_name=track_name,
                artist=artist,
                source='instagram'
            )
        else:
            await msg.edit_text(
                "😕 متأسفانه نتونستم آهنگ رو تشخیص بدم!\n\n"
                "ممکنه:\n"
                "• ویدیو خصوصی باشه\n"
                "• آهنگ نداشته باشه\n"
                "• آهنگ ناشناس باشه"
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در پردازش اینستاگرام: {e}", exc_info=True)
        await msg.edit_text(
            "❌ مشکلی پیش اومد!\n\n"
            "چک کن که:\n"
            "• لینک درست باشه\n"
            "• پست عمومی باشه\n"
            "• ویدیو باشه (نه عکس)"
        )
    finally:
        context.user_data.pop('waiting_for', None)


async def handle_track_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """جستجوی ساده با نام آهنگ"""
    
    msg = await update.message.reply_text(
        f"🔍 در حال جستجو برای: <i>{query}</i>...",
        parse_mode='HTML'
    )
    
    try:
        if not spotify_service.is_available():
            await msg.edit_text("❌ سرویس موزیک در دسترس نیست!")
            return
        
        # جستجو در Spotify
        results = spotify_service.sp.search(q=query, type='track', limit=5)
        tracks = results.get('tracks', {}).get('items', [])
        
        if not tracks:
            await msg.edit_text(
                f"😕 هیچ نتیجه‌ای برای <i>{query}</i> پیدا نشد!",
                parse_mode='HTML'
            )
            return
        
        # اگه فقط یک نتیجه واضح بود، مستقیم بفرست
        if len(tracks) == 1:
            track = tracks[0]
            track_info = spotify_service.format_track_info(track)
            
            await msg.edit_text(
                f"✅ پیدا شد!\n\n"
                f"🎵 {track_info['name']}\n"
                f"🎤 {track_info['artist_str']}\n\n"
                f"📥 در حال ارسال...",
                parse_mode='HTML'
            )
            
            await send_track_to_user(update, context, track_info, 'search')
        else:
            # نمایش چند نتیجه
            keyboard = []
            for idx, track in enumerate(tracks[:5], 1):
                artists = ', '.join([a['name'] for a in track['artists']])
                button_text = f"{idx}. {track['name']} - {artists}"
                if len(button_text) > 60:
                    button_text = button_text[:57] + "..."
                
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"send_track_{track['id']}"
                    )
                ])
            
            await msg.edit_text(
                f"🎵 <b>نتایج برای:</b> <i>{query}</i>\n\n"
                "یکی رو انتخاب کن:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در جستجو: {e}", exc_info=True)
        await msg.edit_text("❌ مشکلی پیش اومد! دوباره امتحان کن.")
    finally:
        context.user_data.pop('waiting_for', None)


async def handle_lyrics_search(update: Update, context: ContextTypes.DEFAULT_TYPE, lyrics_text: str):
    """جستجو با متن آهنگ"""
    
    msg = await update.message.reply_text(
        "🔍 در حال جستجو با متن آهنگ...\n⏳ صبر کن..."
    )
    
    try:
        # جستجوی ساده در Spotify با متن
        results = spotify_service.sp.search(
            q=lyrics_text,
            type='track',
            limit=5
        )
        tracks = results.get('tracks', {}).get('items', [])
        
        if not tracks:
            await msg.edit_text(
                "😕 نتونستم آهنگی با این متن پیدا کنم!\n\n"
                "می‌تونی:\n"
                "• اسم آهنگ رو مستقیم بنویسی\n"
                "• یه ویس از آهنگ بفرستی"
            )
            return
        
        # نمایش نتایج
        keyboard = []
        for idx, track in enumerate(tracks[:5], 1):
            artists = ', '.join([a['name'] for a in track['artists']])
            button_text = f"{idx}. {track['name']} - {artists}"
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"send_track_{track['id']}"
                )
            ])
        
        await msg.edit_text(
            "🎵 <b>آهنگ‌های مشابه:</b>\n\n"
            "کدوم رو می‌خوای؟",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"❌ خطا در جستجو با متن: {e}", exc_info=True)
        await msg.edit_text("❌ مشکلی پیش اومد!")
    finally:
        context.user_data.pop('waiting_for', None)


async def search_and_send_track(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    track_name: str,
    artist: str,
    source: str
):
    """جستجو و ارسال آهنگ تشخیص داده شده"""
    
    try:
        # جستجو در Spotify
        query = f"{track_name} {artist}"
        results = spotify_service.sp.search(q=query, type='track', limit=1)
        tracks = results.get('tracks', {}).get('items', [])
        
        if tracks:
            track = tracks[0]
            track_info = spotify_service.format_track_info(track)
            await send_track_to_user(update, context, track_info, source)
        else:
            await update.message.reply_text(
                f"😕 نتونستم آهنگ رو تو Spotify پیدا کنم!\n\n"
                f"🎵 {track_name}\n"
                f"🎤 {artist}"
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در ارسال: {e}")
        await update.message.reply_text("❌ مشکلی پیش اومد!")


async def send_track_to_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    track_info: dict,
    source: str
):
    """ارسال آهنگ به کاربر"""
    user_id = update.effective_user.id
    
    success = await send_music_to_user(
        bot=context.bot,
        user_id=user_id,
        genre='auto',
        send_to='private',
        download_file=True,
        track_info=track_info
    )
    
    if success:
        # ذخیره در تاریخچه
        db = SessionLocal()
        try:
            db.add(DownloadedTrack(
                user_id=user_id,
                track_id=track_info['id'],
                track_name=track_info['name'],
                artist=track_info['artist_str'],
                source=source,
                download_method='recognition'
            ))
            db.commit()
        finally:
            db.close()



async def handle_send_track_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال آهنگ انتخاب‌شده از نتایج جستجوی سریع/متن."""
    query = update.callback_query
    await query.answer()

    track_id = query.data.replace('send_track_', '', 1)
    try:
        track = spotify_service.sp.track(track_id)
        track_info = spotify_service.format_track_info(track)
        await query.edit_message_text(
            f"✅ انتخاب شد!\n\n"
            f"🎵 {track_info['name']}\n"
            f"🎤 {track_info['artist_str']}\n\n"
            f"📥 در حال ارسال..."
        )
        await send_music_to_user(
            bot=context.bot,
            user_id=update.effective_user.id,
            genre='search',
            send_to='private',
            download_file=True,
            track_info=track_info
        )
    except Exception as e:
        logger.error(f"❌ خطا در ارسال آهنگ انتخاب شده: {e}", exc_info=True)
        await query.edit_message_text("❌ نتونستم این آهنگ رو ارسال کنم. دوباره امتحان کن.")

def get_input_processor_handlers():
    """لیست handler های پردازش ورودی"""
    return [
        MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio_message),
        MessageHandler(filters.VOICE, handle_voice_message),
        MessageHandler(filters.VIDEO, handle_video_message),
        CallbackQueryHandler(handle_send_track_callback, pattern=r'^send_track_'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input),
    ]