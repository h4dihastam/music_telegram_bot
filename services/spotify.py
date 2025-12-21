"""
Spotify Service - جستجو و دریافت اطلاعات آهنگ از Spotify
"""
import random
import logging
from typing import Optional, List, Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from core.config import config

logger = logging.getLogger(__name__)


class SpotifyService:
    """کلاس اصلی برای کار با Spotify API"""
    
    def __init__(self):
        """راه‌اندازی Spotify client"""
        if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
            logger.warning("⚠️ Spotify credentials موجود نیست!")
            self.sp = None
            return
        
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("✅ Spotify Service راه‌اندازی شد")
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی Spotify: {e}")
            self.sp = None
    
    def is_available(self) -> bool:
        """بررسی در دسترس بودن سرویس"""
        return self.sp is not None
    
    # ==================== جستجوی آهنگ ====================
    
    def search_tracks_by_genre(
        self, 
        genre: str, 
        limit: int = 50,
        market: str = 'US'
    ) -> List[Dict[str, Any]]:
        """
        جستجوی آهنگ بر اساس ژانر
        
        Args:
            genre: نام ژانر (مثل pop, rock, jazz)
            limit: تعداد نتایج (حداکثر 50)
            market: بازار (US, GB, IR, ...)
        
        Returns:
            لیست آهنگ‌ها
        """
        if not self.is_available():
            logger.error("❌ Spotify Service در دسترس نیست")
            return []
        
        try:
            # جستجو با query ژانر
            results = self.sp.search(
                q=f'genre:{genre}',
                type='track',
                limit=limit,
                market=market
            )
            
            tracks = results['tracks']['items']
            logger.info(f"✅ {len(tracks)} آهنگ از ژانر {genre} پیدا شد")
            return tracks
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی آهنگ: {e}")
            return []
    
    def search_tracks_by_keyword(
        self,
        keyword: str,
        limit: int = 50,
        market: str = 'US'
    ) -> List[Dict[str, Any]]:
        """
        جستجوی آهنگ با کلمه کلیدی
        
        Args:
            keyword: کلمه کلیدی (مثل "chill pop", "happy jazz")
            limit: تعداد نتایج
            market: بازار
        
        Returns:
            لیست آهنگ‌ها
        """
        if not self.is_available():
            return []
        
        try:
            results = self.sp.search(
                q=keyword,
                type='track',
                limit=limit,
                market=market
            )
            
            tracks = results['tracks']['items']
            logger.info(f"✅ {len(tracks)} آهنگ با کلید '{keyword}' پیدا شد")
            return tracks
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return []
    
    # ==================== انتخاب تصادفی ====================
    
    def get_random_track(
        self, 
        genre: str,
        exclude_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        انتخاب تصادفی یک آهنگ از یک ژانر
        
        Args:
            genre: ژانر موزیک
            exclude_ids: لیست ID های آهنگ‌هایی که نباید انتخاب شوند
        
        Returns:
            اطلاعات آهنگ یا None
        """
        tracks = self.search_tracks_by_genre(genre, limit=50)
        
        if not tracks:
            logger.warning(f"⚠️ هیچ آهنگی از ژانر {genre} پیدا نشد")
            return None
        
        # فیلتر کردن آهنگ‌های تکراری
        if exclude_ids:
            tracks = [t for t in tracks if t['id'] not in exclude_ids]
        
        if not tracks:
            logger.warning("⚠️ همه آهنگ‌ها قبلاً ارسال شده‌اند")
            # اگه همه ارسال شدن، از اول شروع کن
            tracks = self.search_tracks_by_genre(genre, limit=50)
        
        # انتخاب تصادفی
        selected = random.choice(tracks)
        logger.info(f"🎵 آهنگ انتخاب شد: {selected['name']} - {selected['artists'][0]['name']}")
        
        return selected
    
    # ==================== اطلاعات دقیق آهنگ ====================
    
    def get_track_details(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        دریافت اطلاعات کامل یک آهنگ
        
        Args:
            track_id: Spotify ID آهنگ
        
        Returns:
            اطلاعات کامل آهنگ
        """
        if not self.is_available():
            return None
        
        try:
            track = self.sp.track(track_id)
            return track
        except Exception as e:
            logger.error(f"❌ خطا در دریافت اطلاعات آهنگ: {e}")
            return None
    
    def get_track_audio_features(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        دریافت ویژگی‌های صوتی آهنگ (tempo, energy, ...)
        
        Args:
            track_id: Spotify ID آهنگ
        
        Returns:
            ویژگی‌های صوتی
        """
        if not self.is_available():
            return None
        
        try:
            features = self.sp.audio_features(track_id)[0]
            return features
        except Exception as e:
            logger.error(f"❌ خطا در دریافت audio features: {e}")
            return None
    
    # ==================== لینک‌های آهنگ ====================
    
    def get_track_links(self, track: Dict[str, Any]) -> Dict[str, str]:
        """
        استخراج تمام لینک‌های مربوط به آهنگ
        
        Args:
            track: دیکشنری اطلاعات آهنگ
        
        Returns:
            دیکشنری لینک‌ها
        """
        links = {
            'spotify': track.get('external_urls', {}).get('spotify', ''),
            'preview': track.get('preview_url', ''),  # 30 second preview
            'uri': track.get('uri', ''),  # spotify:track:xxxxx
        }
        
        return links
    
    # ==================== فرمت کردن اطلاعات ====================
    
    def format_track_info(self, track: Dict[str, Any]) -> Dict[str, Any]:
        """
        فرمت کردن اطلاعات آهنگ برای استفاده راحت‌تر
        
        Args:
            track: دیکشنری خام از Spotify
        
        Returns:
            دیکشنری فرمت شده
        """
        # استخراج هنرمندان
        artists = [artist['name'] for artist in track.get('artists', [])]
        artist_str = ", ".join(artists)
        
        # استخراج آلبوم
        album = track.get('album', {})
        album_name = album.get('name', 'Unknown')
        
        # تصویر آلبوم
        images = album.get('images', [])
        cover_image = images[0]['url'] if images else None
        
        # مدت زمان (از میلی‌ثانیه به دقیقه:ثانیه)
        duration_ms = track.get('duration_ms', 0)
        duration_min = duration_ms // 60000
        duration_sec = (duration_ms % 60000) // 1000
        duration_str = f"{duration_min}:{duration_sec:02d}"
        
        # تاریخ انتشار
        release_date = album.get('release_date', 'Unknown')
        
        # محبوبیت
        popularity = track.get('popularity', 0)
        
        # لینک‌ها
        links = self.get_track_links(track)
        
        formatted = {
            'id': track.get('id', ''),
            'name': track.get('name', 'Unknown'),
            'artists': artists,
            'artist_str': artist_str,
            'album': album_name,
            'duration': duration_str,
            'duration_ms': duration_ms,
            'release_date': release_date,
            'popularity': popularity,
            'cover_image': cover_image,
            'links': links,
            'preview_url': track.get('preview_url'),
        }
        
        return formatted
    
    # ==================== جستجوی پیشرفته ====================
    
    def search_by_mood(
        self,
        mood: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        جستجوی آهنگ بر اساس mood (حال و هوا)
        
        Args:
            mood: حال و هوا (happy, sad, energetic, chill, ...)
            limit: تعداد نتایج
        
        Returns:
            لیست آهنگ‌ها
        """
        mood_keywords = {
            'happy': 'happy upbeat positive',
            'sad': 'sad emotional melancholy',
            'energetic': 'energetic pump up workout',
            'chill': 'chill relax calm',
            'romantic': 'romantic love ballad',
            'party': 'party dance club',
        }
        
        keyword = mood_keywords.get(mood.lower(), mood)
        return self.search_tracks_by_keyword(keyword, limit=limit)
    
    def get_recommendations(
        self,
        seed_tracks: List[str] = None,
        seed_artists: List[str] = None,
        seed_genres: List[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        دریافت پیشنهاد آهنگ بر اساس seed ها
        
        Args:
            seed_tracks: لیست ID آهنگ‌ها
            seed_artists: لیست ID هنرمندها
            seed_genres: لیست ژانرها
            limit: تعداد پیشنهاد
        
        Returns:
            لیست آهنگ‌های پیشنهادی
        """
        if not self.is_available():
            return []
        
        try:
            recommendations = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                seed_genres=seed_genres,
                limit=limit
            )
            
            tracks = recommendations['tracks']
            logger.info(f"✅ {len(tracks)} آهنگ پیشنهاد داده شد")
            return tracks
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت recommendations: {e}")
            return []


# ==================== Singleton Instance ====================

# یک instance واحد برای استفاده در کل برنامه
spotify_service = SpotifyService()


# ==================== Helper Functions ====================

def get_random_track_for_user(user_id: int, genre: str) -> Optional[Dict[str, Any]]:
    """
    دریافت یک آهنگ تصادفی برای کاربر (با چک کردن تاریخچه)
    
    Args:
        user_id: شناسه کاربر
        genre: ژانر موزیک
    
    Returns:
        آهنگ فرمت شده یا None
    """
    from core.database import SessionLocal, SentTrack
    
    # گرفتن لیست آهنگ‌های ارسال شده
    db = SessionLocal()
    try:
        sent_tracks = db.query(SentTrack).filter(
            SentTrack.user_id == user_id
        ).order_by(SentTrack.sent_at.desc()).limit(50).all()
        
        exclude_ids = [t.track_id for t in sent_tracks]
        
    finally:
        db.close()
    
    # جستجوی آهنگ تصادفی
    track = spotify_service.get_random_track(genre, exclude_ids=exclude_ids)
    
    if not track:
        return None
    
    # فرمت کردن
    return spotify_service.format_track_info(track)


if __name__ == "__main__":
    # تست سرویس
    print("🧪 در حال تست Spotify Service...")
    
    service = SpotifyService()
    
    if service.is_available():
        print("✅ Spotify در دسترس است")
        
        # تست جستجو
        track = service.get_random_track('pop')
        if track:
            formatted = service.format_track_info(track)
            print(f"\n🎵 آهنگ تصادفی:")
            print(f"   نام: {formatted['name']}")
            print(f"   هنرمند: {formatted['artist_str']}")
            print(f"   آلبوم: {formatted['album']}")
            print(f"   مدت: {formatted['duration']}")
            print(f"   لینک: {formatted['links']['spotify']}")
    else:
        print("❌ Spotify در دسترس نیست - لطفاً credentials را چک کنید")