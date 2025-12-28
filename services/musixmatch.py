"""
Lyrics Service - چند API با fallback بهبود یافته
"""
import logging
import requests
from typing import Optional
from urllib.parse import quote
import time

logger = logging.getLogger(__name__)


class LyricsService:
    """سرویس دریافت متن آهنگ با چند منبع"""
    
    def __init__(self):
        self.cache = {}  # کش ساده برای جلوگیری از درخواست‌های تکراری
        logger.info("✅ Lyrics Service راه‌اندازی شد")
    
    def search_lyrics(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """جستجو در چند API"""
        
        # چک کش
        cache_key = f"{artist_name}:{track_name}".lower()
        if cache_key in self.cache:
            logger.info("✅ Lyrics از کش")
            return self.cache[cache_key]
        
        # روش 1: lyrics.ovh
        lyrics = self._try_lyrics_ovh(track_name, artist_name)
        if lyrics:
            self.cache[cache_key] = lyrics
            return lyrics
        
        # روش 2: API دیگر (اگر داری)
        lyrics = self._try_alternative_api(track_name, artist_name)
        if lyrics:
            self.cache[cache_key] = lyrics
            return lyrics
        
        logger.warning(f"❌ متن پیدا نشد: {track_name} - {artist_name}")
        return None
    
    def _try_lyrics_ovh(self, track_name: str, artist_name: str) -> Optional[str]:
        """تلاش با lyrics.ovh"""
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
                    logger.info("✅ Lyrics از lyrics.ovh")
                    return lyrics.strip()
            elif response.status_code == 404:
                logger.debug("⚠️ lyrics.ovh: آهنگ پیدا نشد")
            else:
                logger.debug(f"⚠️ lyrics.ovh: status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning("⏱️ lyrics.ovh: تایم‌اوت")
        except Exception as e:
            logger.warning(f"⚠️ lyrics.ovh خطا: {e}")
        
        return None
    
    def _try_alternative_api(self, track_name: str, artist_name: str) -> Optional[str]:
        """تلاش با API جایگزین"""
        try:
            # API دیگری که ممکنه کار کنه: api.textyl.co
            url = "https://api.textyl.co/api/lyrics"
            
            params = {
                'q': f"{artist_name} {track_name}"
            }
            
            response = requests.get(
                url,
                params=params,
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                lyrics = data.get('lyrics')
                
                if lyrics and lyrics.strip():
                    logger.info("✅ Lyrics از API جایگزین")
                    return lyrics.strip()
                    
        except Exception as e:
            logger.debug(f"⚠️ API جایگزین: {e}")
        
        return None
    
    def format_lyrics_for_telegram(
        self, 
        lyrics: str, 
        max_lines: int = 8
    ) -> str:
        """فرمت کردن برای تلگرام"""
        if not lyrics:
            return ""
        
        lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
        
        # فقط چند خط اول
        preview_lines = lines[:max_lines]
        preview = '\n'.join(preview_lines)
        
        if len(lines) > max_lines:
            preview += "\n\n[...]"
        
        # محدود کردن طول کل (Telegram caption limit)
        if len(preview) > 800:
            preview = preview[:800] + "..."
        
        return preview


# Singleton
lyrics_service = LyricsService()


def get_track_lyrics(
    track_name: str,
    artist_name: str
) -> Optional[str]:
    """دریافت lyrics"""
    return lyrics_service.search_lyrics(track_name, artist_name)


# تست
if __name__ == "__main__":
    print("🧪 تست Lyrics Service...")
    
    test_cases = [
        ("Blinding Lights", "The Weeknd"),
        ("Shape of You", "Ed Sheeran"),
    ]
    
    for track, artist in test_cases:
        print(f"\n🎵 {track} - {artist}")
        lyrics = get_track_lyrics(track, artist)
        
        if lyrics:
            formatted = lyrics_service.format_lyrics_for_telegram(lyrics)
            print(f"✅ پیدا شد ({len(lyrics)} حرف)")
            print(f"Preview:\n{formatted[:200]}...")
        else:
            print("❌ پیدا نشد")