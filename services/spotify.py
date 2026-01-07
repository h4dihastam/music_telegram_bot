"""
Spotify Service - بهبود یافته برای آهنگ‌های ایرانی
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
    
    # نقشه ژانرها به کلمات کلیدی - بهبود یافته برای ایرانی
    GENRE_KEYWORDS = {
        # ایرانی - بهبود شده
        'persian_pop': [
            'persian pop', 'iranian pop', 'persian music',
            'farsi pop', 'موسیقی ایرانی', 'پاپ فارسی'
        ],
        'persian_traditional': [
            'persian traditional', 'iranian traditional',
            'persian classical', 'radif', 'dastgah',
            'موسیقی سنتی', 'موسیقی اصیل'
        ],
        'persian_rap': [
            'persian rap', 'iranian rap', 'farsi rap',
            'persian hip hop', 'رپ فارسی', 'هیپ هاپ فارسی'
        ],
        
        # جهانی
        'pop': ['pop', 'pop music', 'popular'],
        'rock': ['rock', 'rock music', 'alternative rock'],
        'hiphop': ['hip hop', 'rap', 'hip-hop', 'rapper'],
        'electronic': ['electronic', 'edm', 'dance', 'techno', 'house'],
        'jazz': ['jazz', 'jazz music', 'smooth jazz'],
        'classical': ['classical', 'orchestra', 'symphony'],
        'metal': ['metal', 'heavy metal', 'metalcore'],
        'country': ['country', 'country music', 'nashville'],
        'rnb': ['r&b', 'rnb', 'soul', 'rhythm and blues'],
        'reggae': ['reggae', 'ska', 'dancehall'],
        'latin': ['latin', 'reggaeton', 'salsa', 'bachata'],
        'kpop': ['kpop', 'korean pop', 'k-pop'],
        'indie': ['indie', 'independent', 'indie rock'],
        'blues': ['blues', 'blues music'],
        'folk': ['folk', 'folk music', 'acoustic'],
        'arabic': ['arabic music', 'arab', 'middle eastern'],
        'turkish': ['turkish music', 'turkish pop', 'türkçe']
    }
    
    # پلی‌لیست‌های محبوب - بهبود برای ایرانی
    POPULAR_PLAYLISTS = {
        # ایرانی
        'persian_pop': [
            'Persian Pop Hits', 'Top Persian Music', 'Iranian Pop',
            'Farsi Favorites', 'Best of Persian Pop'
        ],
        'persian_traditional': [
            'Persian Classical', 'Iranian Traditional',
            'Persian Instrumental', 'Radif'
        ],
        'persian_rap': [
            'Persian Rap', 'Iranian Hip Hop', 'Farsi Rap Hits',
            'Underground Persian Rap'
        ],
        
        # جهانی
        'pop': ['Today\'s Top Hits', 'Pop Rising'],
        'rock': ['Rock Classics', 'Rock Mix'],
        'hiphop': ['RapCaviar', 'Hip Hop Mix'],
        'electronic': ['mint', 'Dance Rising'],
        'kpop': ['K-Pop ON!', 'K-Pop Daebak'],
        'arabic': ['Arabic Pop', 'Top Arabic'],
        'turkish': ['Turkish Pop', 'Türkçe Pop']
    }
    
    # هنرمندان ایرانی محبوب (برای جستجوی بهتر)
    PERSIAN_ARTISTS = {
        'persian_pop': [
            'Shadmehr Aghili', 'Mohsen Yeganeh', 'Sirvan Khosravi',
            'Homayoun Shajarian', 'Hamed Behdad', 'Evan Band',
            'Hamid Hiraad', 'Reza Sadeghi', 'Mehdi Ahmadvand'
        ],
        'persian_traditional': [
            'Mohammad Reza Shajarian', 'Hossein Alizadeh',
            'Kayhan Kalhor', 'Shahram Nazeri', 'Alireza Ghorbani'
        ],
        'persian_rap': [
            'Hichkas', 'Zedbazi', 'Erfan', 'Bahram',
            'Ho3ein', 'Gdaal', 'Yas', 'Pishro'
        ]
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
        """جستجوی آهنگ - بهبود یافته برای ایرانی"""
        if not self.is_available():
            logger.error("❌ Spotify Service در دسترس نیست")
            return []
        
        all_tracks = []
        
        try:
            # استراتژی ویژه برای ژانرهای ایرانی
            if genre.startswith('persian_'):
                all_tracks = self._search_persian_tracks(genre, limit)
            else:
                # جستجوی عادی برای ژانرهای دیگر
                all_tracks = self._search_global_tracks(genre, limit, market)
            
            # حذف تکراری
            seen_ids = set()
            unique_tracks = []
            for track in all_tracks:
                if track and track.get('id') and track['id'] not in seen_ids:
                    seen_ids.add(track['id'])
                    unique_tracks.append(track)
            
            logger.info(f"✅ {len(unique_tracks)} آهنگ یونیک از ژانر {genre} پیدا شد")
            return unique_tracks[:limit]
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return []
    
    def _search_persian_tracks(self, genre: str, limit: int) -> List[Dict[str, Any]]:
        """جستجوی ویژه برای آهنگ‌های ایرانی"""
        all_tracks = []
        
        try:
            # روش 1: جستجو با نام هنرمندان ایرانی
            artists = self.PERSIAN_ARTISTS.get(genre, [])
            for artist in artists[:5]:  # 5 هنرمند اول
                try:
                    results = self.sp.search(
                        q=f'artist:"{artist}"',
                        type='track',
                        limit=10,
                        market=''  # بدون محدودیت مارکت
                    )
                    
                    if results['tracks']['items']:
                        all_tracks.extend(results['tracks']['items'])
                        logger.info(f"✅ {len(results['tracks']['items'])} آهنگ از {artist}")
                    
                    if len(all_tracks) >= limit:
                        break
                        
                except Exception as e:
                    logger.debug(f"⚠️ خطا در جستجوی {artist}: {e}")
                    continue
            
            # روش 2: جستجو با کلمات کلیدی فارسی
            if len(all_tracks) < 20:
                keywords = self.GENRE_KEYWORDS.get(genre, [])
                for keyword in keywords[:3]:
                    try:
                        results = self.sp.search(
                            q=keyword,
                            type='track',
                            limit=15,
                            market=''
                        )
                        
                        if results['tracks']['items']:
                            all_tracks.extend(results['tracks']['items'])
                            
                        if len(all_tracks) >= limit:
                            break
                            
                    except:
                        continue
            
            # روش 3: جستجو در playlist های ایرانی
            if len(all_tracks) < 20:
                logger.info("🔍 جستجو در playlist های ایرانی...")
                playlist_tracks = self._search_from_playlists(genre, limit - len(all_tracks))
                all_tracks.extend(playlist_tracks)
            
            logger.info(f"✅ مجموع {len(all_tracks)} آهنگ ایرانی پیدا شد")
            return all_tracks
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی ایرانی: {e}")
            return []
    
    def _search_global_tracks(
        self, 
        genre: str, 
        limit: int,
        market: str
    ) -> List[Dict[str, Any]]:
        """جستجوی عادی برای ژانرهای جهانی"""
        all_tracks = []
        
        keywords = self.GENRE_KEYWORDS.get(genre, [genre])
        
        for keyword in keywords[:3]:
            try:
                results = self.sp.search(
                    q=keyword,
                    type='track',
                    limit=20,
                    market=market
                )
                
                if results['tracks']['items']:
                    all_tracks.extend(results['tracks']['items'])
                    
                if len(all_tracks) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"⚠️ خطا در جستجو با '{keyword}': {e}")
                continue
        
        # جستجو در playlist ها
        if len(all_tracks) < 20:
            playlist_tracks = self._search_from_playlists(genre, limit - len(all_tracks))
            all_tracks.extend(playlist_tracks)
        
        return all_tracks
    
    def _search_from_playlists(self, genre: str, limit: int = 50) -> List[Dict[str, Any]]:
        """جستجو در playlist های محبوب"""
        all_tracks = []
        
        try:
            playlist_names = self.POPULAR_PLAYLISTS.get(genre, [])
            
            for playlist_name in playlist_names:
                try:
                    results = self.sp.search(
                        q=playlist_name,
                        type='playlist',
                        limit=1
                    )
                    
                    if not results['playlists']['items']:
                        continue
                    
                    playlist = results['playlists']['items'][0]
                    
                    tracks_results = self.sp.playlist_tracks(
                        playlist['id'],
                        limit=30
                    )
                    
                    for item in tracks_results['items']:
                        if item and item.get('track') and item['track'].get('id'):
                            all_tracks.append(item['track'])
                            
                        if len(all_tracks) >= limit:
                            break
                            
                except Exception as e:
                    logger.warning(f"⚠️ خطا در playlist '{playlist_name}': {e}")
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
        """دریافت یک آهنگ تصادفی"""
        tracks = self.search_tracks_by_genre(genre, limit=50)
        
        if not tracks:
            logger.warning(f"⚠️ هیچ آهنگی برای ژانر {genre} پیدا نشد")
            # تلاش دوباره با market بین‌المللی
            logger.info("🔄 تلاش با market بین‌المللی...")
            tracks = self.search_tracks_by_genre(genre, limit=50, market='')
        
        if not tracks:
            logger.error(f"❌ همچنان آهنگی پیدا نشد برای {genre}")
            return None
        
        if exclude_ids:
            tracks = [t for t in tracks if t and t.get('id') not in exclude_ids]
        
        if tracks:
            return random.choice(tracks)
        
        return None

    def format_track_info(self, track: Dict[str, Any]) -> Dict[str, Any]:
        """فرمت کردن اطلاعات آهنگ"""
        artists = [a['name'] for a in track.get('artists', [])]
        artist_str = ', '.join(artists) if artists else 'Unknown Artist'
        
        duration_ms = track.get('duration_ms', 0)
        album_name = track.get('album', {}).get('name', 'Unknown Album')
        
        return {
            'id': track['id'],
            'name': track.get('name', 'Unknown Track'),
            'artist_str': artist_str,
            'album': album_name,
            'duration': f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}",
            'duration_ms': duration_ms,
            'links': {
                'spotify': track.get('external_urls', {}).get('spotify', ''),
                'preview': track.get('preview_url')
            }
        }


# Singleton
spotify_service = SpotifyService()


# Helper Functions
def get_random_track_for_user(user_id: int, genre: str) -> Optional[Dict[str, Any]]:
    """دریافت یک آهنگ تصادفی برای کاربر"""
    from core.database import SessionLocal, SentTrack
    
    db = SessionLocal()
    try:
        sent_tracks = db.query(SentTrack).filter(
            SentTrack.user_id == user_id
        ).order_by(SentTrack.sent_at.desc()).limit(100).all()
        
        exclude_ids = [t.track_id for t in sent_tracks]
        
        logger.info(f"🔍 جستجو برای ژانر '{genre}', تعداد exclude: {len(exclude_ids)}")
        
    finally:
        db.close()
    
    track = spotify_service.get_random_track(genre, exclude_ids=exclude_ids)
    
    if not track:
        logger.error(f"❌ آهنگی برای کاربر {user_id} و ژانر {genre} پیدا نشد")
        return None
    
    formatted = spotify_service.format_track_info(track)
    logger.info(f"✅ آهنگ انتخاب شد: {formatted['name']} - {formatted['artist_str']}")
    
    return formatted