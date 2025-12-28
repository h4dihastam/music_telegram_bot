"""
Spotify Service - با جستجوی بهبود یافته + ژانرهای جدید
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
    
    # نقشه ژانرها به کلمات کلیدی جستجو - بهبود یافته
    GENRE_KEYWORDS = {
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
        'kpop': ['kpop', 'korean pop', 'k-pop', 'korean music'],
        'indie': ['indie', 'independent', 'indie rock', 'indie pop'],
        'blues': ['blues', 'blues music', 'rhythm and blues'],
        'folk': ['folk', 'folk music', 'acoustic'],
        # ژانرهای جدید
        'persian': ['persian music', 'iranian music', 'farsi', 'persian pop'],
        'arabic': ['arabic music', 'arab', 'middle eastern'],
        'turkish': ['turkish music', 'turkish pop', 'türkçe']
    }
    
    # پلی‌لیست‌های محبوب برای هر ژانر
    POPULAR_PLAYLISTS = {
        'pop': ['Today\'s Top Hits', 'Pop Rising', 'Pop Mix'],
        'rock': ['Rock Classics', 'Rock Mix', 'Alternative Rock'],
        'hiphop': ['RapCaviar', 'Hip Hop Mix', 'Most Necessary'],
        'electronic': ['mint', 'Dance Rising', 'Electronic Mix'],
        'kpop': ['K-Pop ON!', 'K-Pop Daebak', 'K-Pop Rising'],
        'persian': ['Persian Pop', 'Iranian Music', 'Farsi Hits'],
        'arabic': ['Arabic Pop', 'Top Arabic', 'Arabic Hits'],
        'turkish': ['Turkish Pop', 'Türkçe Pop', 'Turkish Hits']
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
        """جستجوی آهنگ بر اساس ژانر - روش بهبود یافته با fallback"""
        if not self.is_available():
            logger.error("❌ Spotify Service در دسترس نیست")
            return []
        
        all_tracks = []
        
        try:
            # روش 1: جستجو با چند keyword
            keywords = self.GENRE_KEYWORDS.get(genre, [genre])
            
            for keyword in keywords[:3]:  # سه کلمه اول
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
            
            # روش 2: جستجو در پلی‌لیست‌های محبوب
            if len(all_tracks) < 20:
                logger.info(f"⚠️ نتیجه کم ({len(all_tracks)}), جستجو در playlist‌ها...")
                playlist_tracks = self._search_from_playlists(genre, limit - len(all_tracks))
                all_tracks.extend(playlist_tracks)
            
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
    
    def _search_from_playlists(self, genre: str, limit: int = 50) -> List[Dict[str, Any]]:
        """جستجو در playlist‌های محبوب ژانر"""
        all_tracks = []
        
        try:
            # اول از لیست playlist‌های از پیش تعریف شده استفاده کن
            playlist_names = self.POPULAR_PLAYLISTS.get(genre, [])
            
            for playlist_name in playlist_names:
                try:
                    # جستجوی playlist
                    results = self.sp.search(
                        q=playlist_name,
                        type='playlist',
                        limit=1
                    )
                    
                    if not results['playlists']['items']:
                        continue
                    
                    playlist = results['playlists']['items'][0]
                    
                    # دریافت آهنگ‌های playlist
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
            
            # اگر هنوز کم داریم، جستجوی عمومی playlist
            if len(all_tracks) < 10:
                keywords = self.GENRE_KEYWORDS.get(genre, [genre])
                for keyword in keywords[:2]:
                    try:
                        results = self.sp.search(
                            q=f'{keyword} playlist',
                            type='playlist',
                            limit=3
                        )
                        
                        for playlist in results['playlists']['items']:
                            if not playlist:
                                continue
                            
                            try:
                                tracks_results = self.sp.playlist_tracks(
                                    playlist['id'],
                                    limit=20
                                )
                                
                                for item in tracks_results['items']:
                                    if item and item.get('track') and item['track'].get('id'):
                                        all_tracks.append(item['track'])
                                        
                                    if len(all_tracks) >= limit:
                                        break
                                        
                            except:
                                continue
                            
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
        tracks = self.search_tracks_by_genre(genre, limit=50)
        
        if not tracks:
            logger.warning(f"⚠️ هیچ آهنگی برای ژانر {genre} پیدا نشد")
            # تلاش دوباره با market دیگر
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
        """فرمت کردن اطلاعات آهنگ برای نمایش"""
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
        # آهنگ‌های ارسال شده اخیر
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


if __name__ == "__main__":
    print("🧪 در حال تست Spotify Service...")
    
    if spotify_service.is_available():
        print("✅ Spotify در دسترس است")
        
        # تست ژانرهای مختلف
        test_genres = ['pop', 'persian', 'kpop']
        
        for genre in test_genres:
            print(f"\n🎵 تست ژانر: {genre}")
            track = spotify_service.get_random_track(genre)
            if track:
                formatted = spotify_service.format_track_info(track)
                print(f"  نام: {formatted['name']}")
                print(f"  هنرمند: {formatted['artist_str']}")
                print(f"  لینک: {formatted['links']['spotify']}")
            else:
                print(f"  ⚠️ آهنگی پیدا نشد")
    else:
        print("❌ Spotify در دسترس نیست - credentials را چک کنید")