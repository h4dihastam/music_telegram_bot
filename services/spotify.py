"""
Spotify Service - بهبود یافته برای آهنگ‌های فارسی + جلوگیری از تکرار
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
    
    # هنرمندان فارسی محبوب - گسترش یافته
    PERSIAN_ARTISTS = {
        'persian_pop': [
            # پاپ معروف
            'Shadmehr Aghili', 'Mohsen Yeganeh', 'Sirvan Khosravi',
            'Homayoun Shajarian', 'Evan Band', 'Hamid Hiraad',
            'Reza Sadeghi', 'Mehdi Ahmadvand', 'Hamed Behdad',
            'Alireza Talischi', 'Ehsan Khaje Amiri', 'Mohsen Chavoshi',
            'Amir Tataloo', 'Ali Yasini', 'Puzzle Band',
            'Sina Sarlak', 'Saman Jalili', 'Benyamin Bahadori',
            'Farzad Farzin', 'Arash AP', 'Mazyar Fallahi',
            # جدیدترها
            'Sohrab MJ', 'Reza Bahram', 'Ali Abdolmaleki',
            'Shahin Najafi', 'Faraz Bonyadi', 'Sasy Mankan',
        ],
        'persian_traditional': [
            'Mohammad Reza Shajarian', 'Hossein Alizadeh',
            'Kayhan Kalhor', 'Shahram Nazeri', 'Alireza Ghorbani',
            'Parisa', 'Sima Bina', 'Dastan Ensemble',
            'Hamavayan Ensemble', 'Afshin Azizi',
        ],
        'persian_rap': [
            'Hichkas', 'Zedbazi', 'Erfan', 'Bahram',
            'Ho3ein', 'Gdaal', 'Yas', 'Pishro',
            'Sijal', 'Quf', 'Sadegh', 'Shayan Eshraghi',
            'Amir Khalvat', 'Mehrad Hidden', 'AFX',
        ]
    }
    
    # کلمات کلیدی برای جستجو
    GENRE_KEYWORDS = {
        'persian_pop': [
            'persian pop', 'iranian pop', 'farsi pop',
            'persian music', 'iranian music',
        ],
        'persian_traditional': [
            'persian traditional', 'iranian traditional',
            'persian classical', 'radif', 'dastgah',
        ],
        'persian_rap': [
            'persian rap', 'iranian rap', 'farsi rap',
            'persian hip hop', 'iranian hip hop',
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
        'rnb': ['r&b', 'rnb', 'soul'],
        'reggae': ['reggae', 'ska', 'dancehall'],
        'latin': ['latin', 'reggaeton', 'salsa'],
        'kpop': ['kpop', 'korean pop', 'k-pop'],
        'indie': ['indie', 'independent'],
        'blues': ['blues'],
        'folk': ['folk', 'acoustic'],
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
        limit: int = 100,
        market: str = ''
    ) -> List[Dict[str, Any]]:
        """جستجوی آهنگ با تعداد بیشتر"""
        if not self.is_available():
            logger.error("❌ Spotify Service در دسترس نیست")
            return []
        
        all_tracks = []
        
        try:
            # استراتژی ویژه برای ژانرهای فارسی
            if genre.startswith('persian_'):
                all_tracks = self._search_persian_tracks(genre, limit)
            else:
                # جستجوی عادی
                all_tracks = self._search_global_tracks(genre, limit, market)
            
            # حذف تکراری بر اساس track ID
            seen_ids = set()
            unique_tracks = []
            for track in all_tracks:
                if track and track.get('id') and track['id'] not in seen_ids:
                    seen_ids.add(track['id'])
                    unique_tracks.append(track)
            
            logger.info(f"✅ {len(unique_tracks)} آهنگ یونیک از ژانر {genre}")
            return unique_tracks[:limit]
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return []
    
    def _search_persian_tracks(self, genre: str, limit: int) -> List[Dict[str, Any]]:
        """جستجوی گسترده برای آهنگ‌های فارسی"""
        all_tracks = []
        
        try:
            artists = self.PERSIAN_ARTISTS.get(genre, [])
            
            # روش 1: جستجوی هنرمندان (تعداد بیشتر)
            for artist in artists:
                try:
                    results = self.sp.search(
                        q=f'artist:"{artist}"',
                        type='track',
                        limit=20,  # افزایش به 20
                        market=''
                    )
                    
                    if results['tracks']['items']:
                        all_tracks.extend(results['tracks']['items'])
                        logger.info(f"✅ {len(results['tracks']['items'])} آهنگ از {artist}")
                    
                    if len(all_tracks) >= limit:
                        break
                        
                except Exception as e:
                    logger.debug(f"⚠️ خطا در جستجوی {artist}: {e}")
                    continue
            
            # روش 2: جستجو با کلمات کلیدی
            if len(all_tracks) < 50:
                keywords = self.GENRE_KEYWORDS.get(genre, [])
                for keyword in keywords:
                    try:
                        results = self.sp.search(
                            q=keyword,
                            type='track',
                            limit=30,
                            market=''
                        )
                        
                        if results['tracks']['items']:
                            all_tracks.extend(results['tracks']['items'])
                            
                    except:
                        continue
            
            logger.info(f"✅ مجموع {len(all_tracks)} آهنگ فارسی پیدا شد")
            return all_tracks
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی فارسی: {e}")
            return []
    
    def _search_global_tracks(
        self, 
        genre: str, 
        limit: int,
        market: str
    ) -> List[Dict[str, Any]]:
        """جستجوی آهنگ‌های جهانی"""
        all_tracks = []
        
        keywords = self.GENRE_KEYWORDS.get(genre, [genre])
        
        for keyword in keywords[:3]:
            try:
                results = self.sp.search(
                    q=keyword,
                    type='track',
                    limit=50,
                    market=market or 'US'
                )
                
                if results['tracks']['items']:
                    all_tracks.extend(results['tracks']['items'])
                    
                if len(all_tracks) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"⚠️ خطا در جستجو با '{keyword}': {e}")
                continue
        
        return all_tracks
    
    def get_random_track(
        self,
        genre: str,
        exclude_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """دریافت یک آهنگ تصادفی با جلوگیری از تکرار قوی‌تر"""
        # دریافت تعداد زیادی آهنگ
        tracks = self.search_tracks_by_genre(genre, limit=100)
        
        if not tracks:
            logger.warning(f"⚠️ هیچ آهنگی برای ژانر {genre} پیدا نشد")
            return None
        
        # فیلتر کردن آهنگ‌های تکراری
        if exclude_ids:
            original_count = len(tracks)
            tracks = [t for t in tracks if t and t.get('id') not in exclude_ids]
            logger.info(f"📊 فیلتر شد: {original_count} → {len(tracks)} آهنگ")
        
        if not tracks:
            logger.warning("⚠️ همه آهنگ‌ها قبلاً ارسال شده! از اول شروع می‌کنیم")
            # اگر همه فرستاده شدن، از اول شروع کن
            tracks = self.search_tracks_by_genre(genre, limit=100)
        
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
    """دریافت یک آهنگ تصادفی برای کاربر با جلوگیری قوی از تکرار"""
    from core.database import SessionLocal, SentTrack
    
    db = SessionLocal()
    try:
        # دریافت 200 آهنگ آخر (بجای 100)
        sent_tracks = db.query(SentTrack).filter(
            SentTrack.user_id == user_id
        ).order_by(SentTrack.sent_at.desc()).limit(200).all()
        
        exclude_ids = [t.track_id for t in sent_tracks]
        
        logger.info(f"🔍 جستجو برای ژانر '{genre}', exclude: {len(exclude_ids)} آهنگ")
        
    finally:
        db.close()
    
    track = spotify_service.get_random_track(genre, exclude_ids=exclude_ids)
    
    if not track:
        logger.error(f"❌ آهنگی برای کاربر {user_id} و ژانر {genre} پیدا نشد")
        return None
    
    formatted = spotify_service.format_track_info(track)
    logger.info(f"✅ آهنگ انتخاب شد: {formatted['name']} - {formatted['artist_str']}")
    
    return formatted