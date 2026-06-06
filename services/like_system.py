"""
Like System - با fix خطای BadRequest (Message is not modified)
"""
import logging
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.error import BadRequest

from core.database import SessionLocal, LikedTrack

logger = logging.getLogger(__name__)


def get_like_keyboard(track_id: str, user_id: int) -> InlineKeyboardMarkup:
    db = SessionLocal()
    try:
        liked = db.query(LikedTrack).filter(
            LikedTrack.user_id == user_id,
            LikedTrack.track_id == track_id
        ).first()
        
        if liked:
            button = InlineKeyboardButton("💔 حذف از علاقه‌مندی‌ها", callback_data=f"unlike_{track_id}")
        else:
            button = InlineKeyboardButton("❤️ افزودن به علاقه‌مندی‌ها", callback_data=f"like_{track_id}")
        
        return InlineKeyboardMarkup([[button]])
    finally:
        db.close()


async def handle_like_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("like_"):
        track_id = data.replace("like_", "", 1)
        action = "like"
    elif data.startswith("unlike_"):
        track_id = data.replace("unlike_", "", 1)
        action = "unlike"
    else:
        return
    
    db = SessionLocal()
    try:
        if action == "like":
            existing = db.query(LikedTrack).filter(
                LikedTrack.user_id == user_id,
                LikedTrack.track_id == track_id
            ).first()
            
            if existing:
                await query.answer("⚠️ قبلاً لایک کردی!", show_alert=True)
                return
            
            track_info = context.user_data.get('last_track_info', {})
            liked_track = LikedTrack(
                user_id=user_id,
                track_id=track_id,
                track_name=track_info.get('name', 'Unknown'),
                artist=track_info.get('artist_str', 'Unknown'),
                spotify_url=track_info.get('links', {}).get('spotify'),
                preview_url=track_info.get('links', {}).get('preview')
            )
            db.add(liked_track)
            db.commit()
            
            # FIX: catch BadRequest اگه کیبورد تغییر نکرده باشه
            try:
                new_keyboard = get_like_keyboard(track_id, user_id)
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            except BadRequest as e:
                if "not modified" not in str(e).lower():
                    raise
            
            await query.answer("❤️ به علاقه‌مندی‌ها اضافه شد!", show_alert=True)
            
        elif action == "unlike":
            deleted = db.query(LikedTrack).filter(
                LikedTrack.user_id == user_id,
                LikedTrack.track_id == track_id
            ).delete()
            db.commit()
            
            if deleted:
                try:
                    new_keyboard = get_like_keyboard(track_id, user_id)
                    await query.edit_message_reply_markup(reply_markup=new_keyboard)
                except BadRequest as e:
                    if "not modified" not in str(e).lower():
                        raise
                
                await query.answer("💔 از علاقه‌مندی‌ها حذف شد!", show_alert=True)
            else:
                await query.answer("⚠️ این آهنگ رو لایک نکرده بودی!", show_alert=True)
    
    except BadRequest as e:
        if "not modified" in str(e).lower():
            pass  # خطای بی‌خطر - نادیده بگیر
        else:
            logger.error(f"❌ BadRequest در لایک: {e}")
            await query.answer("❌ مشکلی پیش اومد!", show_alert=True)
            db.rollback()
    except Exception as e:
        logger.error(f"❌ خطا در لایک: {e}", exc_info=True)
        await query.answer("❌ مشکلی پیش اومد!", show_alert=True)
        db.rollback()
    finally:
        db.close()


def get_like_handler():
    return CallbackQueryHandler(handle_like_callback, pattern=r'^(like_|unlike_)')


def get_liked_tracks_list(user_id: int, limit: int = 50) -> list:
    db = SessionLocal()
    try:
        liked = db.query(LikedTrack).filter(
            LikedTrack.user_id == user_id
        ).order_by(LikedTrack.liked_at.desc()).limit(limit).all()
        return [
            {
                'track_id': t.track_id,
                'track_name': t.track_name,
                'artist': t.artist,
                'spotify_url': t.spotify_url,
                'liked_at': t.liked_at
            }
            for t in liked
        ]
    finally:
        db.close()


def is_track_liked(user_id: int, track_id: str) -> bool:
    db = SessionLocal()
    try:
        return db.query(LikedTrack).filter(
            LikedTrack.user_id == user_id,
            LikedTrack.track_id == track_id
        ).first() is not None
    finally:
        db.close()
