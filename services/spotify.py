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
        جستجوی آهنگ بر اساس کلمه کلیدی
        
        Args:
            keyword: کلمه کلیدی جستجو
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
            logger.info(f"✅ {len(tracks)} آهنگ برای '{keyword}' پیدا شد")
            return tracks
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return []

    def get_random_track(
        self,
        genre: str,
        exclude_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        دریافت یک آهنگ تصادفی از ژانر
        
        Args:
            genre: ژانر
            exclude_ids: لیست IDهایی که تکراری نباشن
        
        Returns:
            اطلاعات آهنگ یا None
        """
        tracks = self.search_tracks_by_genre(genre)
        if not tracks:
            return None
        
        if exclude_ids:
            tracks = [t for t in tracks if t['id'] not in exclude_ids]
        
        if tracks:
            return random.choice(tracks)
        return None

    def format_track_info(self, track: Dict[str, Any]) -> Dict[str, Any]:
        """
        فرمت کردن اطلاعات آهنگ برای نمایش
        
        Args:
            track: اطلاعات خام از Spotify
        
        Returns:
            دیکشنری فرمت شده
        """
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

    def get_recommendations(
        self,
        seed_tracks: List[str] = None,
        seed_artists: List[str] = None,
        seed_genres: List[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        دریافت recommendations از Spotify
        
        Args:
            seed_tracks: لیست ID آهنگ‌ها
            seed_artists: لیست ID هنرمندان
            seed_genres: لیست ژانرها
            limit: تعداد
        
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
            return