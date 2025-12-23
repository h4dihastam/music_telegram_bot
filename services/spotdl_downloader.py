"""
Downloader با spotDL - دانلود آهنگ با کیفیت بالا از Spotify (با metadata کامل)
"""
import logging
import os
from pathlib import Path
from typing import Optional

from spotdl import SpotifyClient, Spotdl

logger = logging.getLogger(__name__)

# مسیر دانلود
DOWNLOAD_DIR = Path("/app/downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# راه‌اندازی spotDL
spotify_client = SpotifyClient()
spotdl_client = Spotdl(spotify_client)

class SpotDLDownloader:
    """کلاس دانلود با spotDL"""

    def download_track(
        self,
        track_name: str,
        artist_name: str,
        spotify_url: Optional[str] = None
    ) -> Optional[str]:
        """
        دانلود آهنگ با spotDL

        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند
            spotify_url: لینک Spotify (اگر داری بهتره)

        Returns:
            مسیر فایل MP3 یا None
        """
        try:
            query = f"{artist_name} {track_name}"
            if spotify_url:
                query = spotify_url

            logger.info(f"📥 در حال دانلود با spotDL: {query}")

            # دانلود
            results = spotdl_client.search([query])
            if not results:
                logger.warning("⚠️ آهنگ پیدا نشد در spotDL")
                return None

            song = results[0]

            # دانلود با metadata کامل
            downloaded_path = spotdl_client.download(song, folder=str(DOWNLOAD_DIR))

            if not downloaded_path or not os.path.exists(downloaded_path):
                logger.warning("⚠️ فایل دانلود شده پیدا نشد")
                return None

            logger.info(f"✅ دانلود موفق با spotDL: {downloaded_path}")
            return str(downloaded_path)

        except Exception as e:
            logger.error(f"❌ خطا در دانلود با spotDL: {e}")
            return None

    def cleanup_old_files(self, max_age_hours: int = 6):
        """پاک کردن فایل‌های قدیمی"""
        from datetime import datetime, timedelta
        now = datetime.now()
        for file in DOWNLOAD_DIR.iterdir():
            if file.is_file():
                age = now - datetime.fromtimestamp(file.stat().st_mtime)
                if age > timedelta(hours=max_age_hours):
                    file.unlink()
                    logger.info(f"🗑️ فایل قدیمی حذف شد: {file}")


# Singleton
spotdl_downloader = SpotDLDownloader()


# Helper function
def download_spotdl_safe(
    track_name: str,
    artist_name: str,
    spotify_url: Optional[str] = None
) -> Optional[str]:
    """دانلود ایمن با cleanup"""
    spotdl_downloader.cleanup_old_files()
    return spotdl_downloader.download_track(track_name, artist_name, spotify_url)