# downloader.py - در فولدر services/
"""
Downloader Service - دانلود فایل کامل آهنگ از YouTube (برای prototype آموزشی)
⚠️ هشدار: این بخش فقط برای prototype دانشگاهی است و ممکن است قوانین YouTube/کپی‌رایت را نقض کند.
در نسخه واقعی، فقط از preview 30 ثانیه Spotify استفاده کنید!
"""

import logging
import os
from typing import Optional
import yt_dlp
from youtube_search import YoutubeSearch

from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """کلاس برای دانلود آهنگ از YouTube"""
    
    def __init__(self):
        """راه‌اندازی downloader"""
        self.download_dir = config.DOWNLOADS_DIR
        logger.info("✅ Music Downloader راه‌اندازی شد (برای prototype)")
    
    def search_youtube(self, query: str) -> Optional[str]:
        """
        جستجو در YouTube برای لینک ویدیو
        
        Args:
            query: عبارت جستجو (مثل "song name artist official audio")
        
        Returns:
            لینک ویدیو یا None
        """
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            if not results:
                logger.warning(f"⚠️ نتیجه‌ای برای '{query}' پیدا نشد")
                return None
            
            video_id = results[0]['id']
            return f"https://www.youtube.com/watch?v={video_id}"
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return None
    
    def download_audio(
        self,
        url: str,
        output_file: str
    ) -> Optional[str]:
        """
        دانلود فایل صوتی از YouTube
        
        Args:
            url: لینک ویدیو
            output_file: نام فایل خروجی (بدون پسوند)
        
        Returns:
            مسیر فایل دانلود شده یا None
        """
        ydl_opts = {
            'format': config.DOWNLOAD_QUALITY,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f"{self.download_dir}/{output_file}.%(ext)s",
            'quiet': True,
            'no_warnings': True,
            'continuedl': False,
            'restrictfilenames': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            mp3_path = f"{self.download_dir}/{output_file}.mp3"
            
            if not os.path.exists(mp3_path):
                logger.warning("⚠️ فایل دانلود نشد!")
                return None
            
            file_size = os.path.getsize(mp3_path) / (1024 * 1024)
            if file_size > config.MAX_DOWNLOAD_SIZE_MB:
                logger.warning(f"⚠️ فایل خیلی بزرگ است: {file_size:.2f} MB")
                os.remove(mp3_path)
                return None
            
            logger.info(f"✅ فایل دانلود شد: {mp3_path} ({file_size:.2f} MB)")
            return mp3_path
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
            return None
    
    def cleanup_file(self, file_path: str):
        """پاک کردن فایل موقت"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"✅ فایل پاک شد: {file_path}")
        except Exception as e:
            logger.error(f"❌ خطا در پاک کردن فایل: {e}")


# Singleton instance
music_downloader = MusicDownloader()


# Helper function
def download_track_safe(
    track_name: str,
    artist_name: str
) -> Optional[str]:
    """
    دانلود ایمن آهنگ (با جستجو و دانلود)
    
    Args:
        track_name: نام آهنگ
        artist_name: نام هنرمند
    
    Returns:
        مسیر فایل MP3 یا None
    """
    query = f"{track_name} {artist_name} official audio"
    
    url = music_downloader.search_youtube(query)
    if not url:
        return None
    
    output_file = f"{track_name.replace(' ', '_')}_{artist_name.replace(' ', '_')}"
    
    return music_downloader.download_audio(url, output_file)


if __name__ == "__main__":
    # تست downloader
    print("🧪 تست Music Downloader...")
    
    downloader = MusicDownloader()
    
    test_path = download_track_safe("Shape of You", "Ed Sheeran")
    if test_path:
        print(f"✅ دانلود موفق: {test_path}")
        downloader.cleanup_file(test_path)
    else:
        print("❌ دانلود ناموفق")