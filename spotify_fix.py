"""
Spotify Service - با fallback به جستجوی مستقیم yt-dlp
"""
import random
import logging
from typing import Optional, List, Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from core.config import config

logger = logging.getLogger(__name__)


class SpotifyService:
    
    PERSIAN_ARTISTS = {
        'persian_pop': [
            'Shadmehr Aghili', 'Mohsen Yeganeh', 'Sirvan Khosravi',
            'Homayoun Shajarian', 'Evan Band', 'Hamid Hiraad',
            'Reza Sadeghi', 'Mehdi Ahmadvand', 'Alireza Talischi',
            'Ehsan Khaje Amiri', 'Mohsen Chavoshi', 'Amir Tataloo',
            'Puzzle Band', 'Sina Sarlak', 'Saman Jalili',
            'Benyamin Bahadori', 'Farzad Farzin', 'Mazyar Fallahi',
            'Sohrab MJ', 'Reza Bahram', 'Ali Abdolmaleki',
        ],
        'persian_traditional': [
            'Mohammad Reza Shajarian', 'Hossein Alizadeh',
            'Kayhan Kalhor', 'Shahram Nazeri', 'Alireza Ghorbani',
            'Parisa', 'Sima Bina',
        ],
        'persian_rap': [
            'Hichkas', 'Zedbazi', 'Erfan', 'Bahram',
            'Ho3ein', 'Gdaal', 'Yas', 'Pishro',
            'Sijal', 'Sadegh', 'Mehrad Hidden',
        ]
    }
    
    GENRE_KEYWORDS = {
        'persian_pop': ['persian pop', 'iranian pop', 'farsi pop'],
        'persian_traditional': ['persian traditional', 'iranian classical'],
        'persian_rap': ['persian rap', 'iranian rap', 'farsi rap'],
        'pop': ['pop', 'pop music'],
        'rock': ['rock', 'alternative rock'],
        'hiphop': ['hip hop', 'rap'],
        'electronic': ['electronic', 'edm', 'dance'],
        'jazz': ['jazz'],
        'classical': ['classical', 'orchestra'],
        'metal': ['metal', 'heavy metal'],
        'country': ['country music'],
        'rnb': ['r&b', 'soul'],
        'reggae': ['reggae'],
        'latin': ['latin', 'reggaeton'],
        'kpop': ['kpop', 'k-pop'],
        'indie': ['indie'],
        'blues': ['blues'],
        'folk': ['folk', 'acoustic'],
    }
    
    def __init__(self):
        if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
            logger.warning("⚠️ Spotify credentials موجود نیست!")
            self.sp = None
            self._spotify_available = False
            return
        
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            # تست اولیه برای چک Premium
            self._spotify_available = self._test_spotify_access()
            if self._spotify_available:
                logger.info("✅ Spotify Service راه‌اندازی شد")
            else:
                logger.warning("⚠️ Spotify Search در دسترس نیست (نیاز به Premium) - از fallback استفاده می‌شه")
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی Spotify: {e}")
            self.sp = None
            self._spotify_available = False

    def _test_spotify_access(self) -> bool:
        """چک می‌کنه که آیا search کار می‌کنه"""
        try:
            result = self.sp.search(q='test', type='track', limit=1, market='US')
            return True
        except Exception as e:
            if '403' in str(e) or 'premium' in str(e).lower():
                return False
            return True

    def is_available(self) -> bool:
        return self.sp is not None

    def is_search_available(self) -> bool:
        return self._spotify_available if hasattr(self, '_spotify_available') else False

    def search_tracks_by_genre(self, genre: str, limit: int = 50, market: str = '') -> List[Dict[str, Any]]:
        if not self.is_available():
            return []

        # اگه Spotify search کار نمی‌کنه، آهنگ‌های فارسی رو از هنرمندان بساز
        if not self.is_search_available():
            return self._build_tracks_from_artists(genre, limit)

        all_tracks = []
        try:
            if genre.startswith('persian_'):
                all_tracks = self._search_persian_tracks(genre, limit)
            else:
                all_tracks = self._search_global_tracks(genre, limit, market)

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
            # fallback به ساخت دستی
            return self._build_tracks_from_artists(genre, limit)

    def _build_tracks_from_artists(self, genre: str, limit: int) -> List[Dict[str, Any]]:
        """
        وقتی Spotify search کار نمی‌کنه،
        لیست مصنوعی از هنرمندان می‌سازیم تا yt-dlp بتونه دانلود کنه
        """
        artists = self.PERSIAN_ARTISTS.get(genre, [])
        
        # برای ژانرهای غیر فارسی، کلمات کلیدی رو به عنوان هنرمند در نظر می‌گیریم
        if not artists:
            keywords = self.GENRE_KEYWORDS.get(genre, [genre])
            artists = keywords
        
        fake_tracks = []
        for artist in artists:
            # یه track مصنوعی می‌سازیم - yt-dlp بعداً دانلود می‌کنه
            fake_tracks.append({
                'id': f'ytdlp_{hash(artist) % 100000}',
                'name': '',  # خالی - از هنرمند جستجو می‌شه
                'artist_name': artist,
                'artists': [{'name': artist}],
                'album': {'name': 'Unknown'},
                'duration_ms': 210000,
                'external_urls': {'spotify': ''},
                'preview_url': None,
                '_needs_search': True,  # flag که بگه باید جستجو بشه
            })

        random.shuffle(fake_tracks)
        return fake_tracks[:limit]

    def _search_persian_tracks(self, genre: str, limit: int) -> List[Dict[str, Any]]:
        all_tracks = []
        artists = self.PERSIAN_ARTISTS.get(genre, [])
        
        for artist in artists:
            try:
                results = self.sp.search(
                    q=f'artist:"{artist}"',
                    type='track',
                    limit=10,
                    market=''
                )
                if results['tracks']['items']:
                    all_tracks.extend(results['tracks']['items'])
                if len(all_tracks) >= limit:
                    break
            except Exception as e:
                logger.debug(f"⚠️ خطا در جستجوی {artist}: {e}")
                continue

        if len(all_tracks) < 10:
            keywords = self.GENRE_KEYWORDS.get(genre, [])
            for keyword in keywords:
                try:
                    results = self.sp.search(q=keyword, type='track', limit=20, market='')
                    if results['tracks']['items']:
                        all_tracks.extend(results['tracks']['items'])
                except:
                    continue

        return all_tracks

    def _search_global_tracks(self, genre: str, limit: int, market: str) -> List[Dict[str, Any]]:
        all_tracks = []
        keywords = self.GENRE_KEYWORDS.get(genre, [genre])
        
        for keyword in keywords[:3]:
            try:
                results = self.sp.search(
                    q=keyword, type='track', limit=50, market=market or 'US'
                )
                if results['tracks']['items']:
                    all_tracks.extend(results['tracks']['items'])
                if len(all_tracks) >= limit:
                    break
            except Exception as e:
                logger.warning(f"⚠️ خطا در جستجو با '{keyword}': {e}")
                continue

        return all_tracks

    def get_random_track(self, genre: str, exclude_ids: List[str] = None) -> Optional[Dict[str, Any]]:
        tracks = self.search_tracks_by_genre(genre, limit=50)
        
        if not tracks:
            logger.warning(f"⚠️ هیچ آهنگی برای ژانر {genre} پیدا نشد")
            return None
        
        if exclude_ids:
            original_count = len(tracks)
            tracks = [t for t in tracks if t and t.get('id') not in exclude_ids]
            logger.info(f"📊 فیلتر: {original_count} → {len(tracks)} آهنگ")
        
        if not tracks:
            tracks = self.search_tracks_by_genre(genre, limit=50)
        
        return random.choice(tracks) if tracks else None

    def format_track_info(self, track: Dict[str, Any]) -> Dict[str, Any]:
        artists = [a['name'] for a in track.get('artists', [])]
        artist_str = ', '.join(artists) if artists else track.get('artist_name', 'Unknown Artist')
        
        duration_ms = track.get('duration_ms', 0)
        album_name = track.get('album', {}).get('name', 'Unknown Album')
        
        return {
            'id': track.get('id', ''),
            'name': track.get('name', '') or artist_str,  # اگه نام خالی بود، هنرمند
            'artist_str': artist_str,
            'album': album_name,
            'duration': f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}",
            'duration_ms': duration_ms,
            'links': {
                'spotify': track.get('external_urls', {}).get('spotify', ''),
                'preview': track.get('preview_url')
            },
            '_needs_search': track.get('_needs_search', False),
        }


spotify_service = SpotifyService()


def get_random_track_for_user(user_id: int, genre: str) -> Optional[Dict[str, Any]]:
    from core.database import SessionLocal, SentTrack
    
    db = SessionLocal()
    try:
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
