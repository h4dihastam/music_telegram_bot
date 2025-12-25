"""
Music Downloader با spotDL - نسخه اصلاح شده
"""
import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from spotdl import Spotdl
from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """دانلودر موزیک با spotDL"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        
        try:
            # ✅ اصلاح شده: حذف آرگومان‌های output, format, bitrate که باعث خطا می‌شدند
            self.spotdl = Spotdl(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET
            )
            logger.info("✅ SpotDL راه‌اندازی شد")
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی spotDL: {e}")
            self.spotdl = None
    
    def is_available(self) -> bool:
        """چک کردن در دسترس بودن"""
        return self.spotdl is not None
    
    def _change_dir_and_download(self, song_obj):
        """تغییر مسیر موقت و دانلود"""
        original_cwd = os.getcwd()
        try:
            # رفتن به پوشه دانلود قبل از شروع
            os.chdir(self.download_dir)
            results = self.spotdl.download(song_obj)
            return results
        except Exception as e:
            raise e
        finally:
            # برگشتن به مسیر اصلی
            os.chdir(original_cwd)

    def download_from_spotify_url(self, spotify_url: str) -> Optional[str]:
        """
        دانلود مستقیم از لینک Spotify
        """
        if not self.is_available():
            logger.error("❌ spotDL در دسترس نیست")
            return None
        
        try:
            logger.info(f"📥 دانلود از Spotify: {spotify_url}")
            
            # جستجوی آهنگ
            songs = self.spotdl.search([spotify_url])
            
            if not songs:
                logger.warning("⚠️ آهنگ پیدا نشد")
                return None
            
            song = songs[0]
            # ✅ دانلود با مدیریت مسیر
            results = self._change_dir_and_download(song)
            
            # بررسی نتیجه (spotdl معمولا یک لیست یا مسیر برمی‌گرداند)
            if results:
                # اگر لیست بود اولین آیتم، اگر نه خود مسیر
                file_path = results[0] if isinstance(results, list) else results
                full_path = self.download_dir / Path(file_path).name
                
                if full_path.exists():
                    logger.info(f"✅ دانلود موفق: {full_path}")
                    return str(full_path)
            
            logger.warning("⚠️ فایل دانلود شد اما پیدا نشد")
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
            # ✅ دانلود با مدیریت مسیر
            results = self._change_dir_and_download(song)
            
            if results:
                file_path = results[0] if isinstance(results, list) else results
                full_path = self.download_dir / Path(file_path).name
                
                if full_path.exists():
                    logger.info(f"✅ دانلود موفق")
                    return str(full_path)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
            return None
    
    def download_preview_from_spotify(self, preview_url: str) -> Optional[str]:
        """دانلود preview 30 ثانیه"""
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
            if not self.download_dir.exists():
                return
                
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
    """دانلود ایمن با چند سطح fallback"""
    music_downloader.cleanup_old_files()
    
    if spotify_url:
        file_path = music_downloader.download_from_spotify_url(spotify_url)
        if file_path: return file_path
    
    file_path = music_downloader.download_by_search(track_name, artist_name)
    if file_path: return file_path
    
    if preview_url:
        logger.warning("⚠️ استفاده از preview (30 ثانیه)")
        return music_downloader.download_preview_from_spotify(preview_url)
    
    logger.error("❌ تمام روش‌های دانلود شکست خورد")
    return None