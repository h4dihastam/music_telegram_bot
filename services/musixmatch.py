"""
Lyrics Service - چند API با fallback
"""
import logging
import requests
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class LyricsService:
    """سرویس دریافت متن آهنگ با چند منبع"""
    
    def __init__(self):
        logger.info("✅ Lyrics Service راه‌اندازی شد")
    
    def search_lyrics(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """جستجو در API"""
        
        # سعی با lyrics.ovh
        try:
            url = f"https://api.lyrics.ovh/v1/{quote(artist_name)}/{quote(track_name)}"
            
            response = requests.get(
                url,
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                lyrics = data.get('lyrics')
                
                if lyrics and lyrics.strip():
                    logger.info(f"✅ Lyrics از lyrics.ovh")
                    return lyrics.strip()
        except Exception as e:
            logger.warning(f"⚠️ lyrics.ovh ناموفق: {e}")
        
        logger.warning(f"❌ متن پیدا نشد: {track_name} - {artist_name}")
        return None
    
    def format_lyrics_for_telegram(
        self, 
        lyrics: str, 
        max_lines: int = 6
    ) -> str:
        """فرمت کردن برای تلگرام"""
        if not lyrics:
            return ""
        
        lines = lyrics.split('\n')
        
        # فقط چند خط اول
        preview_lines = lines[:max_lines]
        preview = '\n'.join(preview_lines)
        
        if len(lines) > max_lines:
            preview += "\n..."
        
        return preview


# Singleton
lyrics_service = LyricsService()


def get_track_lyrics(
    track_name: str,
    artist_name: str
) -> Optional[str]:
    """دریافت lyrics"""
    return lyrics_service.search_lyrics(track_name, artist_name)