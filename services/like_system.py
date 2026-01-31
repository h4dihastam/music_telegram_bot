"""
سیستم لایک آهنگ‌ها با دکمه Inline
"""
import logging
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from core.database import SessionLocal, LikedTrack

logger = logging.getLogger(__name__)


def get_like_keyboard(track_id: str, user_id: int) -> InlineKeyboardMarkup:
    """
    ساخت کیبورد لایک
    
    Args:
        track_id: آیدی آهنگ
        user_id: آیدی کاربر
    
    Returns:
        کیبورد با دکمه لایک/آنلایک
    """
    db = SessionLocal()
    try:
        # چک کنیم که آیا کاربر این آهنگ رو لایک کرده
        liked = db.query(LikedTrack).filter(
            LikedTrack.user_id == user_id,
            LikedTrack.track_id == track_id
        ).first()
        
        if liked:
            # لایک شده - دکمه آنلایک
            button = InlineKeyboardButton(
                "💔 حذف از علاقه‌مندی‌ها",
                callback_data=f"unlike_{track_id}"
            )
        else:
            # لایک نشده - دکمه لایک
            button = InlineKeyboardButton(
                "❤️ افزودن به علاقه‌مندی‌ها",
                callback_data=f"like_{track_id}"
            )
        
        return InlineKeyboardMarkup([[button]])
        
    finally:
        db.close()


async def handle_like_callback(update, context):
    """پردازش کلیک روی دکمه لایک"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # استخراج track_id
    if data.startswith("like_"):
        track_id = data.replace("like_", "")
        action = "like"
    elif data.startswith("unlike_"):
        track_id = data.replace("unlike_", "")
        action = "unlike"
    else:
        return
    
    db = SessionLocal()
    try:
        if action == "like":
            # چک کنیم که قبلاً لایک نکرده باشه
            existing = db.query(LikedTrack).filter(
                LikedTrack.user_id == user_id,
                LikedTrack.track_id == track_id
            ).first()
            
            if existing:
                await query.answer("⚠️ قبلاً لایک کردی!", show_alert=True)
                return
            
            # دریافت اطلاعات آهنگ از context (اگه موجود باشه)
            track_info = context.user_data.get('last_track_info', {})
            
            # لایک کردن
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
            
            # بروزرسانی دکمه
            new_keyboard = get_like_keyboard(track_id, user_id)
            await query.edit_message_reply_markup(reply_markup=new_keyboard)
            
            await query.answer("❤️ به علاقه‌مندی‌ها اضافه شد!", show_alert=True)
            
            logger.info(f"✅ کاربر {user_id} آهنگ {track_id} رو لایک کرد")
            
        elif action == "unlike":
            # آنلایک کردن
            deleted = db.query(LikedTrack).filter(
                LikedTrack.user_id == user_id,
                LikedTrack.track_id == track_id
            ).delete()
            db.commit()
            
            if deleted:
                # بروزرسانی دکمه
                new_keyboard = get_like_keyboard(track_id, user_id)
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
                
                await query.answer("💔 از علاقه‌مندی‌ها حذف شد!", show_alert=True)
                
                logger.info(f"✅ کاربر {user_id} آهنگ {track_id} رو آنلایک کرد")
            else:
                await query.answer("⚠️ این آهنگ رو لایک نکرده بودی!", show_alert=True)
    
    except Exception as e:
        logger.error(f"❌ خطا در لایک/آنلایک: {e}", exc_info=True)
        await query.answer("❌ مشکلی پیش اومد!", show_alert=True)
        db.rollback()
    finally:
        db.close()


def get_like_handler():
    """handler لایک"""
    return CallbackQueryHandler(
        handle_like_callback,
        pattern=r'^(like_|unlike_)'
    )


# Helper functions

def get_liked_tracks_list(user_id: int, limit: int = 50) -> list:
    """دریافت لیست آهنگ‌های لایک شده"""
    db = SessionLocal()
    try:
        liked = db.query(LikedTrack).filter(
            LikedTrack.user_id == user_id
        ).order_by(LikedTrack.liked_at.desc()).limit(limit).all()
        
        return [
            {
                'track_id': track.track_id,
                'track_name': track.track_name,
                'artist': track.artist,
                'spotify_url': track.spotify_url,
                'preview_url': track.preview_url,
                'liked_at': track.liked_at
            }
            for track in liked
        ]
    finally:
        db.close()


def is_track_liked(user_id: int, track_id: str) -> bool:
    """چک کردن لایک بودن آهنگ"""
    db = SessionLocal()
    try:
        liked = db.query(LikedTrack).filter(
            LikedTrack.user_id == user_id,
            LikedTrack.track_id == track_id
        ).first()
        
        return liked is not None
    finally:
        db.close()