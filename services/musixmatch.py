"""
Musixmatch Service - دریافت متن (lyrics) آهنگ‌ها
"""
import logging
import requests
from typing import Optional, Dict, Any
from core.config import config

logger = logging.getLogger(__name__)


class MusixmatchService:
    """کلاس برای کار با Musixmatch API"""
    
    BASE_URL = "https://api.musixmatch.com/ws/1.1"
    
    def __init__(self):
        """راه‌اندازی Musixmatch service"""
        self.api_key = config.MUSIXMATCH_API_KEY
        
        if not self.api_key:
            logger.warning("⚠️ Musixmatch API Key موجود نیست!")
        else:
            logger.info("✅ Musixmatch Service راه‌اندازی شد")
    
    def is_available(self) -> bool:
        """بررسی در دسترس بودن سرویس"""
        return self.api_key is not None and self.api_key != ""
    
    # ==================== جستجوی آهنگ ====================
    
    def search_track(
        self, 
        track_name: str, 
        artist_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        جستجوی آهنگ در Musixmatch
        
        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند (اختیاری)
        
        Returns:
            اطلاعات آهنگ یا None
        """
        if not self.is_available():
            logger.warning("⚠️ Musixmatch در دسترس نیست")
            return None
        
        try:
            params = {
                'apikey': self.api_key,
                'q_track': track_name,
                'page_size': 1,
                'page': 1,
                's_track_rating': 'desc'  # بهترین match
            }
            
            if artist_name:
                params['q_artist'] = artist_name
            
            response = requests.get(
                f"{self.BASE_URL}/track.search",
                params=params,
                timeout=10
            )
            
            data = response.json()
            
            # چک کردن status code
            if data['message']['header']['status_code'] != 200:
                logger.warning(f"⚠️ Musixmatch error: {data['message']['header']['status_code']}")
                return None
            
            # چک کردن وجود نتیجه
            track_list = data['message']['body'].get('track_list', [])
            if not track_list:
                logger.warning(f"⚠️ آهنگ پیدا نشد: {track_name}")
                return None
            
            track = track_list[0]['track']
            logger.info(f"✅ آهنگ پیدا شد: {track['track_name']} - {track['artist_name']}")
            
            return track
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی آهنگ: {e}")
            return None
    
    # ==================== دریافت Lyrics ====================
    
    def get_lyrics(
        self, 
        track_id: int
    ) -> Optional[str]:
        """
        دریافت متن کامل آهنگ
        
        Args:
            track_id: شناسه آهنگ در Musixmatch
        
        Returns:
            متن آهنگ یا None
        """
        if not self.is_available():
            return None
        
        try:
            params = {
                'apikey': self.api_key,
                'track_id': track_id
            }
            
            response = requests.get(
                f"{self.BASE_URL}/track.lyrics.get",
                params=params,
                timeout=10
            )
            
            data = response.json()
            
            # چک کردن status
            if data['message']['header']['status_code'] != 200:
                logger.warning(f"⚠️ Lyrics پیدا نشد برای track_id: {track_id}")
                return None
            
            lyrics_body = data['message']['body'].get('lyrics', {})
            lyrics_text = lyrics_body.get('lyrics_body', '')
            
            if not lyrics_text:
                return None
            
            # پاک کردن متن اضافه در آخر
            # Musixmatch متن اضافه می‌ذاره در آخر
            if "******* This Lyrics is NOT for Commercial use *******" in lyrics_text:
                lyrics_text = lyrics_text.split("******* This Lyrics is NOT for Commercial use *******")[0]
            
            lyrics_text = lyrics_text.strip()
            
            logger.info(f"✅ Lyrics دریافت شد ({len(lyrics_text)} کاراکتر)")
            return lyrics_text
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت lyrics: {e}")
            return None
    
    def get_lyrics_by_name(
        self, 
        track_name: str, 
        artist_name: str = None
    ) -> Optional[str]:
        """
        دریافت متن آهنگ با نام آهنگ و هنرمند
        
        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند
        
        Returns:
            متن آهنگ یا None
        """
        # اول آهنگ رو پیدا کن
        track = self.search_track(track_name, artist_name)
        
        if not track:
            return None
        
        # حالا lyrics رو بگیر
        track_id = track['track_id']
        return self.get_lyrics(track_id)
    
    # ==================== دریافت Snippet ====================
    
    def get_lyrics_snippet(
        self,
        track_name: str,
        artist_name: str = None,
        max_lines: int = 4
    ) -> Optional[str]:
        """
        دریافت snippet (قسمت کوچکی) از lyrics
        برای نمایش در پیام
        
        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند
            max_lines: حداکثر تعداد خطوط
        
        Returns:
            snippet متن یا None
        """
        lyrics = self.get_lyrics_by_name(track_name, artist_name)
        
        if not lyrics:
            return None
        
        # گرفتن چند خط اول
        lines = lyrics.split('\n')
        snippet_lines = lines[:max_lines]
        snippet = '\n'.join(snippet_lines)
        
        # اگه lyrics بیشتر از snippet بود، ... اضافه کن
        if len(lines) > max_lines:
            snippet += "\n..."
        
        return snippet
    
    # ==================== Cache Management ====================
    
    def get_cached_lyrics(
        self,
        track_id_spotify: str,
        track_name: str,
        artist_name: str
    ) -> Optional[str]:
        """
        دریافت lyrics با استفاده از cache
        
        Args:
            track_id_spotify: Spotify ID
            track_name: نام آهنگ
            artist_name: نام هنرمند
        
        Returns:
            متن آهنگ
        """
        from core.database import SessionLocal, TrackCache
        import json
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        try:
            # چک کردن cache
            cached = db.query(TrackCache).filter(
                TrackCache.track_id == track_id_spotify
            ).first()
            
            # اگه cache موجود بود و تازه بود (کمتر از 30 روز)
            if cached and cached.lyrics:
                cache_age = datetime.utcnow() - cached.cached_at
                if cache_age < timedelta(days=30):
                    logger.info(f"✅ Lyrics از cache بارگذاری شد")
                    return cached.lyrics
            
            # اگه cache نبود یا قدیمی بود، از API بگیر
            lyrics = self.get_lyrics_by_name(track_name, artist_name)
            
            if lyrics:
                # ذخیره در cache
                if cached:
                    cached.lyrics = lyrics
                    cached.cached_at = datetime.utcnow()
                else:
                    new_cache = TrackCache(
                        track_id=track_id_spotify,
                        track_data=json.dumps({'name': track_name, 'artist': artist_name}),
                        lyrics=lyrics
                    )
                    db.add(new_cache)
                
                db.commit()
                logger.info(f"✅ Lyrics در cache ذخیره شد")
            
            return lyrics
            
        finally:
            db.close()
    
    # ==================== Format Lyrics ====================
    
    def format_lyrics_for_message(
        self,
        lyrics: str,
        max_length: int = 1000
    ) -> str:
        """
        فرمت کردن lyrics برای نمایش در پیام تلگرام
        
        Args:
            lyrics: متن کامل
            max_length: حداکثر طول
        
        Returns:
            متن فرمت شده
        """
        if not lyrics:
            return "❌ متن آهنگ در دسترس نیست"
        
        # اگه خیلی طولانی بود، کوتاه کن
        if len(lyrics) > max_length:
            lyrics = lyrics[:max_length]
            # از آخرین خط کامل استفاده کن
            last_newline = lyrics.rfind('\n')
            if last_newline > 0:
                lyrics = lyrics[:last_newline]
            lyrics += "\n\n... (متن کامل در لینک)"
        
        # اضافه کردن emoji و فرمت
        formatted = f"📝 متن آهنگ:\n\n{lyrics}"
        
        return formatted


# ==================== Singleton Instance ====================

musixmatch_service = MusixmatchService()


# ==================== Helper Function ====================

def get_track_lyrics(
    track_name: str,
    artist_name: str,
    spotify_id: str = None,
    use_cache: bool = True
) -> Optional[str]:
    """
    Helper function برای دریافت lyrics
    
    Args:
        track_name: نام آهنگ
        artist_name: نام هنرمند
        spotify_id: Spotify ID (برای cache)
        use_cache: استفاده از cache
    
    Returns:
        متن آهنگ
    """
    if use_cache and spotify_id:
        return musixmatch_service.get_cached_lyrics(
            spotify_id,
            track_name,
            artist_name
        )
    else:
        return musixmatch_service.get_lyrics_by_name(
            track_name,
            artist_name
        )


if __name__ == "__main__":
    # تست سرویس
    print("🧪 در حال تست Musixmatch Service...")
    
    service = MusixmatchService()
    
    if service.is_available():
        print("✅ Musixmatch در دسترس است")
        
        # تست جستجو
        lyrics = service.get_lyrics_by_name("Shape of You", "Ed Sheeran")
        
        if lyrics:
            print(f"\n📝 متن آهنگ:")
            print(lyrics[:200] + "..." if len(lyrics) > 200 else lyrics)
        else:
            print("❌ متن پیدا نشد")
    else:
        print("❌ Musixmatch در دسترس نیست - API Key را چک کنید")