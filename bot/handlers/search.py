"""
Handler جستجوی موزیک - قابلیت جستجوی پیشرفته
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from services.spotify import spotify_service
from services.music_sender import send_music_to_user
from core.database import SessionLocal, DownloadedTrack

logger = logging.getLogger(__name__)

# States
SEARCHING, SELECTING = range(2)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /search - شروع جستجو"""
    await update.message.reply_text(
        "🔍 <b>جستجوی موزیک</b>\n\n"
        "اسم آهنگ یا خواننده رو بنویس:\n"
        "مثال:\n"
        "• Blinding Lights\n"
        "• The Weeknd\n"
        "• Homayoun Shajarian آواز دل\n\n"
        "<i>برای لغو، /cancel بزن</i>",
        parse_mode='HTML'
    )
    
    return SEARCHING


async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش جستجو"""
    query = update.message.text.strip()
    
    msg = await update.message.reply_text(
        f"🔍 در حال جستجو برای: <i>{query}</i>...",
        parse_mode='HTML'
    )
    
    try:
        if not spotify_service.is_available():
            await msg.edit_text("❌ سرویس موزیک در دسترس نیست!")
            return ConversationHandler.END
        
        # جستجو در Spotify
        results = spotify_service.sp.search(q=query, type='track', limit=10)
        tracks = results.get('tracks', {}).get('items', [])
        
        if not tracks:
            await msg.edit_text(
                f"😕 هیچ نتیجه‌ای برای <i>{query}</i> پیدا نشد!\n\n"
                "دوباره امتحان کن یا /cancel بزن.",
                parse_mode='HTML'
            )
            return SEARCHING
        
        # ذخیره نتایج
        context.user_data['search_results'] = tracks
        
        # نمایش نتایج
        keyboard = []
        for idx, track in enumerate(tracks[:10], 1):
            artists = ', '.join([a['name'] for a in track['artists']])
            button_text = f"{idx}. {track['name']} - {artists}"
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"search_select_{idx-1}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ لغو", callback_data="search_cancel")
        ])
        
        await msg.edit_text(
            f"🎵 <b>نتایج برای:</b> <i>{query}</i>\n\n"
            "یکی رو انتخاب کن:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return SELECTING
        
    except Exception as e:
        logger.error(f"❌ خطا در جستجو: {e}", exc_info=True)
        await msg.edit_text("❌ مشکلی پیش اومد! دوباره امتحان کن.")
        return ConversationHandler.END


async def handle_track_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش انتخاب آهنگ"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "search_cancel":
        await query.edit_message_text("❌ جستجو لغو شد!")
        return ConversationHandler.END
    
    # استخراج index
    try:
        idx = int(data.split("_")[-1])
        tracks = context.user_data.get('search_results', [])
        
        if idx >= len(tracks):
            await query.answer("❌ خطا!", show_alert=True)
            return ConversationHandler.END
        
        track = tracks[idx]
        track_info = spotify_service.format_track_info(track)
        
        await query.edit_message_text(
            f"✅ انتخاب شد!\n\n"
            f"🎵 {track_info['name']}\n"
            f"🎤 {track_info['artist_str']}\n\n"
            f"📥 در حال ارسال..."
        )
        
        # ارسال به کاربر
        user_id = update.effective_user.id
        
        success = await send_music_to_user(
            bot=context.bot,
            user_id=user_id,
            genre='search',
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
                    source='search',
                    download_method='manual_search'
                ))
                db.commit()
            finally:
                db.close()
        
        # پاک کردن cache
        if 'search_results' in context.user_data:
            del context.user_data['search_results']
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ خطا در انتخاب: {e}", exc_info=True)
        await query.edit_message_text("❌ مشکلی پیش اومد!")
        return ConversationHandler.END


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو جستجو"""
    if update.message:
        await update.message.reply_text("❌ جستجو لغو شد!")
    
    if 'search_results' in context.user_data:
        del context.user_data['search_results']
    
    return ConversationHandler.END


def get_search_conversation_handler():
    """ساخت conversation handler برای جستجو"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('search', search_command)
        ],
        states={
            SEARCHING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_search_query
                )
            ],
            SELECTING: [
                CallbackQueryHandler(
                    handle_track_selection,
                    pattern=r'^search_(select_|cancel)'
                )
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_search),
            CallbackQueryHandler(
                cancel_search,
                pattern=r'^search_cancel$'
            )
        ],
        per_user=True,
        name="search_conversation"
    )