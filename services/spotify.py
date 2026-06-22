"""
Spotify Service - با جستجوی بهبود یافته
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
    
    # نقشه ژانرها به کلمات کلیدی جستجو
    GENRE_KEYWORDS = {
        'pop': 'pop',
        'rock': 'rock',
        'hiphop': 'hip hop rap',
        'electronic': 'electronic dance edm',
        'jazz': 'jazz',
        'classical': 'classical orchestra',
        'metal': 'metal',
        'country': 'country',
        'rnb': 'r&b rnb soul',
        'reggae': 'reggae',
        'latin': 'latin reggaeton',
        'kpop': 'kpop korean',  # ✅ اصلاح شد
        'indie': 'indie alternative',
        'blues': 'blues',
        'folk': 'folk acoustic'
    }
    
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
        """جستجوی آهنگ بر اساس ژانر - روش بهبود یافته"""
        if not self.is_available():
            logger.error("❌ Spotify Service در دسترس نیست")
            return []
        
        try:
            # استفاده از کلمات کلیدی بهتر
            search_query = self.GENRE_KEYWORDS.get(genre, genre)
            
            # روش 1: جستجو با کلمات کلیدی
            results = self.sp.search(
                q=search_query,
                type='track',
                limit=limit,
                market=market
            )
            
            tracks = results['tracks']['items']
            
            # اگر نتیجه‌ای نبود، از playlist‌های محبوب استفاده کن
            if len(tracks) < 10:
                logger.info(f"⚠️ نتیجه کم، جستجو در playlist‌ها...")
                tracks = self._search_from_playlists(genre, limit)
            
            logger.info(f"✅ {len(tracks)} آهنگ از ژانر {genre} پیدا شد")
            return tracks
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return []
    
    def _search_from_playlists(self, genre: str, limit: int = 50) -> List[Dict[str, Any]]:
        """جستجو در playlist‌های محبوب ژانر"""
        try:
            search_query = self.GENRE_KEYWORDS.get(genre, genre)
            
            # جستجوی playlist
            playlists = self.sp.search(
                q=search_query,
                type='playlist',
                limit=5
            )
            
            all_tracks = []
            
            for playlist in playlists['playlists']['items']:
                if not playlist:
                    continue
                    
                try:
                    # دریافت آهنگ‌های playlist
                    results = self.sp.playlist_tracks(
                        playlist['id'],
                        limit=20
                    )
                    
                    for item in results['items']:
                        if item['track'] and item['track'] not in all_tracks:
                            all_tracks.append(item['track'])
                            
                        if len(all_tracks) >= limit:
                            break
                            
                except:
                    continue
                
                if len(all_tracks) >= limit:
                    break
            
            logger.info(f"✅ {len(all_tracks)} آهنگ از playlist‌ها")
            return all_tracks[:limit]
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی playlist: {e}")
            return []
    
    def get_random_track(
        self,
        genre: str,
        exclude_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """دریافت یک آهنگ تصادفی از ژانر"""
        tracks = self.search_tracks_by_genre(genre)
        
        if not tracks:
            logger.warning(f"⚠️ هیچ آهنگی برای ژانر {genre} پیدا نشد")
            return None
        
        if exclude_ids:
            tracks = [t for t in tracks if t and t.get('id') not in exclude_ids]
        
        if tracks:
            return random.choice(tracks)
        return None

    def format_track_info(self, track: Dict[str, Any]) -> Dict[str, Any]:
        """فرمت کردن اطلاعات آهنگ برای نمایش"""
        artists = [a['name'] for a in track['artists']]
        artist_str = ', '.join(artists)
        
        duration_ms = track.get('duration_ms', 0)
        
        return {
            'id': track['id'],
            'name': track['name'],
            'artist_str': artist_str,
            'album': track['album']['name'],
            'duration': f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}",
            'duration_ms': duration_ms,  # ✅ اضافه شد
            'links': {
                'spotify': track['external_urls']['spotify'],
                'preview': track.get('preview_url')
            }
        }


# ==================== Singleton Instance ====================

spotify_service = SpotifyService()


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

        exclude_ids = [t.track_id for t in sent_tracks if t.track_id]
    finally:
        db.close()

    # تلاش اول: بدون تکرار آهنگ‌های اخیر
    track = spotify_service.get_random_track(genre, exclude_ids=exclude_ids)

    # fallback: اگر pool خالی شد یا API نتیجه نداد، یکبار بدون exclude تلاش کن
    if not track:
        logger.info(
            f"ℹ️ fallback: تلاش مجدد بدون exclude_ids برای کاربر {user_id}، ژانر {genre}"
        )
        track = spotify_service.get_random_track(genre, exclude_ids=None)

    if not track:
        logger.warning(f"⚠️ آهنگی برای کاربر {user_id} و ژانر {genre} پیدا نشد")
        return None

    return spotify_service.format_track_info(track)



if __name__ == "__main__":
    print("🧪 در حال تست Spotify Service...")
    
    if spotify_service.is_available():
        print("✅ Spotify در دسترس است")
        track = spotify_service.get_random_track('kpop')
        if track:
            formatted = spotify_service.format_track_info(track)
            print(f"نام: {formatted['name']}")
            print(f"هنرمند: {formatted['artist_str']}")
            print(f"لینک: {formatted['links']['spotify']}")
        else:
            print("⚠️ آهنگی پیدا نشد")
    else:
        print("❌ Spotify در دسترس نیست - credentials را چک کنید")