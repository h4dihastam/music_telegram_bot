"""
Music Downloader با spotDL - بهترین کیفیت و سریع‌ترین
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from spotdl import Spotdl
from spotdl.types.song import Song

from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """دانلودر موزیک با spotDL"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        
        try:
            # راه‌اندازی spotdl
            self.spotdl = Spotdl(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
                output=str(self.download_dir),
                format="mp3",
                bitrate="192k",
            )
            logger.info("✅ SpotDL راه‌اندازی شد")
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی spotDL: {e}")
            self.spotdl = None
    
    def is_available(self) -> bool:
        """چک کردن در دسترس بودن"""
        return self.spotdl is not None
    
    def download_from_spotify_url(self, spotify_url: str) -> Optional[str]:
        """
        دانلود مستقیم از لینک Spotify
        """
        if not self.is_available():
            logger.error("❌ spotDL در دسترس نیست")
            return None
        
        try:
            logger.info(f"📥 دانلود از Spotify: {spotify_url}")
            
            # دانلود
            songs = self.spotdl.search([spotify_url])
            
            if not songs:
                logger.warning("⚠️ آهنگ پیدا نشد")
                return None
            
            song = songs[0]
            results = self.spotdl.download(song)
            
            if results and os.path.exists(results):
                logger.info(f"✅ دانلود موفق: {results}")
                return results
            
            logger.warning("⚠️ فایل دانلود نشد")
            return None
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
            return None
    
    def download_by_search(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """
        دانلود با جستجو (fallback)
        """
        if not self.is_available():
            return None
        
        try:
            query = f"{artist_name} {track_name}"
            logger.info(f"🔍 جستجو و دانلود: {query}")
            
            songs = self.spotdl.search([query])
            
            if not songs:
                logger.warning("⚠️ نتیجه‌ای پیدا نشد")
                return None
            
            song = songs[0]
            results = self.spotdl.download(song)
            
            if results and os.path.exists(results):
                logger.info(f"✅ دانلود موفق")
                return results
            
            return None
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
            return None
    
    def download_preview_from_spotify(
        self, 
        preview_url: str
    ) -> Optional[str]:
        """
        دانلود preview 30 ثانیه (fallback نهایی)
        """
        try:
            import requests
            import hashlib
            
            file_hash = hashlib.md5(preview_url.encode()).hexdigest()[:8]
            file_name = f"preview_{file_hash}.mp3"
            file_path = self.download_dir / file_name
            
            logger.info("📥 دانلود preview از Spotify...")
            response = requests.get(preview_url, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info("✅ Preview دانلود شد")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود preview: {e}")
            return None
    
    def cleanup_old_files(self, max_age_hours: int = 6):
        """پاک کردن فایل‌های قدیمی"""
        now = datetime.now()
        deleted = 0
        
        try:
            for file in self.download_dir.iterdir():
                if file.is_file():
                    age = now - datetime.fromtimestamp(file.stat().st_mtime)
                    if age > timedelta(hours=max_age_hours):
                        file.unlink()
                        deleted += 1
            
            if deleted > 0:
                logger.info(f"🗑️ {deleted} فایل قدیمی پاک شد")
        except Exception as e:
            logger.error(f"❌ خطا در cleanup: {e}")


# Singleton instance
music_downloader = MusicDownloader()


def download_track_safe(
    track_name: str,
    artist_name: str,
    spotify_url: Optional[str] = None,
    preview_url: Optional[str] = None
) -> Optional[str]:
    """
    دانلود ایمن با چند سطح fallback
    """
    # Cleanup قبل از دانلود
    music_downloader.cleanup_old_files()
    
    # روش 1: از لینک Spotify (بهترین کیفیت)
    if spotify_url:
        file_path = music_downloader.download_from_spotify_url(spotify_url)
        if file_path:
            return file_path
    
    # روش 2: جستجو و دانلود
    file_path = music_downloader.download_by_search(track_name, artist_name)
    if file_path:
        return file_path
    
    # روش 3: Preview 30 ثانیه (آخرین راه)
    if preview_url:
        logger.warning("⚠️ استفاده از preview (30 ثانیه)")
        return music_downloader.download_preview_from_spotify(preview_url)
    
    logger.error("❌ تمام روش‌های دانلود شکست خورد")
    return None