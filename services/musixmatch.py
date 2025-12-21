"""
Musixmatch Unofficial Service - رایگان با community key (از Strvm/musicxmatch-api)
"""
import logging
from typing import Optional
from musicxmatch_api import MusixMatchAPI  # این رو ایمپورت کن

logger = logging.getLogger(__name__)

class UnofficialMusixmatchService:
    """کلاس برای دریافت lyrics رایگان"""
    
    def __init__(self):
        self.api = MusixMatchAPI()  # نیازی به key نیست!
        logger.info("✅ Unofficial Musixmatch Service (رایگان) راه‌اندازی شد")
    
    def search_tracks(self, track_name: str, artist_name: Optional[str] = None):
        """جستجو آهنگ و گرفتن track_id"""
        try:
            query = track_name
            if artist_name:
                query += f" {artist_name}"
            results = self.api.search_tracks(query)
            if results and 'message' in results and 'body' in results['message']:
                track_list = results['message']['body'].get('track_list', [])
                if track_list:
                    return track_list[0]['track']  # اولین نتیجه بهترینه
            return None
        except Exception as e:
            logger.error(f"خطا در جستجو: {e}")
            return None
    
    def get_lyrics_by_id(self, track_id: int) -> Optional[str]:
        """دریافت lyrics با track_id"""
        try:
            response = self.api.get_track_lyrics(track_id=track_id)
            if response and 'message' in response and 'body' in response['message']:
                lyrics_body = response['message']['body'].get('lyrics', {}).get('lyrics_body')
                return lyrics_body or "متن آهنگ پیدا نشد."
            return None
        except Exception as e:
            logger.error(f"خطا در دریافت lyrics: {e}")
            return None
    
    def get_lyrics(self, track_name: str, artist_name: str) -> Optional[str]:
        """دریافت lyrics با نام آهنگ و هنرمند"""
        track_info = self.search_tracks(track_name, artist_name)
        if track_info and 'track_id' in track_info:
            return self.get_lyrics_by_id(track_info['track_id'])
        return "متن آهنگ پیدا نشد."

# Singleton instance
musixmatch_service = UnofficialMusixmatchService()

# Helper function (برای استفاده در music_sender.py)
def get_track_lyrics(track_name: str, artist_name: str) -> str:
    lyrics = musixmatch_service.get_lyrics(track_name, artist_name)
    return lyrics or "متن آهنگ در دسترس نیست."