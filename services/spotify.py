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
    
    def search_tracks_by_genre(
        self, 
        genre: str, 
        limit: int = 50,
        market: str = 'US'
    ) -> List[Dict[str, Any]]:
        """جستجوی آهنگ بر اساس ژانر"""
        if not self.is_available():
            logger.error("❌ Spotify Service در دسترس نیست")
            return []
        
        try:
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
            logger.error(f"❌ خطا در جستجو: {e}")
            return []
    
    def get_random_track(
        self,
        genre: str,
        exclude_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """دریافت یک آهنگ تصادفی از ژانر"""
        tracks = self.search_tracks_by_genre(genre)
        if not tracks:
            return None
        
        if exclude_ids:
            tracks = [t for t in tracks if t['id'] not in exclude_ids]
        
        if tracks:
            return random.choice(tracks)
        return None

    def format_track_info(self, track: Dict[str, Any]) -> Dict[str, Any]:
        """فرمت کردن اطلاعات آهنگ برای نمایش"""
        artists = [a['name'] for a in track['artists']]
        artist_str = ', '.join(artists)
        
        return {
            'id': track['id'],
            'name': track['name'],
            'artist_str': artist_str,
            'album': track['album']['name'],
            'duration': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}",
            'links': {
                'spotify': track['external_urls']['spotify'],
                'preview': track.get('preview_url')
            }
        }


# ==================== Singleton Instance ====================

spotify_service = SpotifyService()  # این خط خیلی مهمه! بدون این، ایمپورت شکست می‌خوره


# ==================== Helper Functions ====================

def get_random_track_for_user(user_id: int, genre: str) -> Optional[Dict[str, Any]]:
    """
    دریافت یک آهنگ تصادفی برای کاربر (با چک کردن تاریخچه تکراری)
    """
    from core.database import SessionLocal, SentTrack
    
    db = SessionLocal()
    try:
        sent_tracks = db.query(SentTrack).filter(
            SentTrack.user_id == user_id
        ).order_by(SentTrack.sent_at.desc()).limit(50).all()
        
        exclude_ids = [t.track_id for t in sent_tracks]
    finally:
        db.close()
    
    track = spotify_service.get_random_track(genre, exclude_ids=exclude_ids)
    
    if not track:
        return None
    
    return spotify_service.format_track_info(track)


if __name__ == "__main__":
    print("🧪 در حال تست Spotify Service...")
    
    if spotify_service.is_available():
        print("✅ Spotify در دسترس است")
        track = spotify_service.get_random_track('pop')
        if track:
            formatted = spotify_service.format_track_info(track)
            print(f"نام: {formatted['name']}")
            print(f"هنرمند: {formatted['artist_str']}")
            print(f"لینک: {formatted['links']['spotify']}")
    else:
        print("❌ Spotify در دسترس نیست - credentials را چک کنید")