"""
Music Downloader با spotDL - نسخه اصلاح شده و بهینه
"""
import os
import logging
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import spotdl
from spotdl.types.options import DownloaderOptionalOptions
from spotdl.types.song import Song
from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """دانلودر موزیک با spotDL"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        
        try:
            # تنظیمات دانلود
            downloader_options = DownloaderOptionalOptions(
                output=str(self.download_dir),
                format='mp3',
                bitrate='320k',
                threads=2,
                cookie_file=None,
                sponsor_block=False,
            )
            
            # راه‌اندازی spotDL با تنظیمات جدید
            self.spotdl = spotdl.Spotdl(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
                downloader_settings=downloader_options,
                user_auth=False
            )
            logger.info("✅ SpotDL راه‌اندازی شد")
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی spotDL: {e}")
            self.spotdl = None
    
    def is_available(self) -> bool:
        """چک کردن در دسترس بودن"""
        return self.spotdl is not None
    
    def _create_song_object(self, query: str) -> Optional[Song]:
        """ایجاد شیء Song از query"""
        try:
            # جستجو و ایجاد Song object
            songs = self.spotdl.search([query])
            if songs and len(songs) > 0:
                return songs[0]
        except Exception as e:
            logger.error(f"❌ خطا در ایجاد Song object: {e}")
        return None
    
    def download_from_spotify_url(self, spotify_url: str) -> Optional[str]:
        """
        دانلود مستقیم از لینک Spotify
        """
        if not self.is_available():
            logger.error("❌ spotDL در دسترس نیست")
            return None
        
        try:
            logger.info(f"📥 دانلود از Spotify: {spotify_url}")
            
            # ایجاد Song object از URL
            songs = self.spotdl.search([spotify_url])
            if not songs:
                logger.warning("⚠️ آهنگ پیدا نشد")
                return None
            
            song = songs[0]
            
            # دانلود آهنگ
            results = self.spotdl.download(song)
            
            if results:
                # نتایج می‌تواند لیست مسیرها باشد
                file_paths = results if isinstance(results, list) else [results]
                
                for file_path in file_paths:
                    if isinstance(file_path, str) and os.path.exists(file_path):
                        logger.info(f"✅ دانلود موفق: {file_path}")
                        return file_path
                    
                    # اگر مسیر نسبی است، مطلقش کن
                    full_path = self.download_dir / Path(file_path).name
                    if full_path.exists():
                        logger.info(f"✅ دانلود موفق: {full_path}")
                        return str(full_path)
            
            logger.warning("⚠️ فایل دانلود شد اما پیدا نشد")
            return None
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود از Spotify: {e}")
            return None
    
    def download_by_search(self, track_name: str, artist_name: str) -> Optional[str]:
        """
        دانلود با جستجو
        """
        if not self.is_available():
            return None
        
        try:
            query = f"{artist_name} {track_name}"
            logger.info(f"🔍 جستجو و دانلود: {query}")
            
            # جستجوی آهنگ
            songs = self.spotdl.search([query])
            if not songs:
                logger.warning("⚠️ نتیجه‌ای پیدا نشد")
                return None
            
            song = songs[0]
            logger.info(f"🎵 آهنگ پیدا شد: {song.display_name}")
            
            # دانلود آهنگ
            results = self.spotdl.download(song)
            
            if results:
                file_paths = results if isinstance(results, list) else [results]
                
                for file_path in file_paths:
                    if isinstance(file_path, str) and os.path.exists(file_path):
                        logger.info(f"✅ دانلود موفق: {file_path}")
                        return file_path
                    
                    full_path = self.download_dir / Path(file_path).name
                    if full_path.exists():
                        logger.info(f"✅ دانلود موفق: {full_path}")
                        return str(full_path)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
            return None
    
    def download_preview_from_spotify(self, preview_url: str) -> Optional[str]:
        """دانلود preview 30 ثانیه"""
        try:
            import urllib.parse
            
            # نام فایل را از URL بساز
            parsed_url = urllib.parse.urlparse(preview_url)
            path = parsed_url.path
            track_id = os.path.basename(path).replace('.mp3', '')
            
            file_name = f"preview_{track_id}.mp3"
            file_path = self.download_dir / file_name
            
            # اگر قبلاً دانلود شده، برگردان
            if file_path.exists():
                logger.info(f"✅ Preview از کش بازیابی شد")
                return str(file_path)
            
            logger.info("📥 دانلود preview از Spotify...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(preview_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # ذخیره فایل
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info("✅ Preview دانلود شد")
            return str(file_path)
            
        except requests.exceptions.Timeout:
            logger.error("❌ تایم‌اوت در دانلود preview")
            return None
        except Exception as e:
            logger.error(f"❌ خطا در دانلود preview: {e}")
            return None
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """دریافت اطلاعات فایل"""
        try:
            if not os.path.exists(file_path):
                return {}
            
            stat = os.stat(file_path)
            size_mb = stat.st_size / (1024 * 1024)
            
            return {
                'path': file_path,
                'size_mb': round(size_mb, 2),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'exists': True
            }
        except Exception as e:
            logger.error(f"❌ خطا در دریافت اطلاعات فایل: {e}")
            return {}
    
    def cleanup_old_files(self, max_age_hours: int = 6):
        """پاک کردن فایل‌های قدیمی"""
        now = datetime.now()
        deleted = 0
        
        try:
            if not self.download_dir.exists():
                return
                
            for file in self.download_dir.iterdir():
                if file.is_file():
                    # فقط فایل‌های موقت یا preview را پاک کن
                    if file.name.startswith('preview_') or file.name.endswith('.temp'):
                        age = now - datetime.fromtimestamp(file.stat().st_mtime)
                        if age > timedelta(hours=max_age_hours):
                            try:
                                file.unlink()
                                deleted += 1
                                logger.debug(f"🗑️ فایل قدیمی پاک شد: {file.name}")
                            except Exception as e:
                                logger.error(f"❌ خطا در پاک کردن {file.name}: {e}")
            
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
    Returns: مسیر فایل دانلود شده یا None
    """
    
    # پاک‌سازی فایل‌های قدیمی
    music_downloader.cleanup_old_files()
    
    # استراتژی ۱: دانلود از Spotify URL
    if spotify_url:
        logger.info("🎯 تلاش برای دانلود از Spotify URL...")
        file_path = music_downloader.download_from_spotify_url(spotify_url)
        if file_path:
            logger.info("✅ دانلود از Spotify URL موفق بود")
            return file_path
    
    # استراتژی ۲: دانلود با جستجو
    logger.info("🎯 تلاش برای دانلود با جستجو...")
    file_path = music_downloader.download_by_search(track_name, artist_name)
    if file_path:
        logger.info("✅ دانلود با جستجو موفق بود")
        return file_path
    
    # استراتژی ۳: دانلود preview (30 ثانیه)
    if preview_url:
        logger.info("🎯 تلاش برای دانلود preview...")
        file_path = music_downloader.download_preview_from_spotify(preview_url)
        if file_path:
            logger.warning("⚠️ فقط preview 30 ثانیه‌ای دانلود شد")
            return file_path
    
    logger.error("❌ تمام روش‌های دانلود شکست خورد")
    return None


def validate_download_file(file_path: str, min_size_kb: int = 100) -> bool:
    """اعتبارسنجی فایل دانلود شده"""
    try:
        if not file_path or not os.path.exists(file_path):
            return False
        
        size_kb = os.path.getsize(file_path) / 1024
        if size_kb < min_size_kb:
            logger.warning(f"⚠️ فایل بسیار کوچک است: {size_kb:.1f}KB")
            os.remove(file_path)
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ خطا در اعتبارسنجی فایل: {e}")
        return False


# تست ساده
if __name__ == "__main__":
    print("🧪 تست Music Downloader...")
    
    # تنظیم logging
    logging.basicConfig(level=logging.INFO)
    
    if music_downloader.is_available():
        print("✅ Downloader در دسترس است")
        
        # تست دانلود preview (برای تست سریع)
        test_url = "https://p.scdn.co/mp3-preview/..."
        print(f"🔍 تست دانلود preview...")
        
        result = music_downloader.download_preview_from_spotify(
            "https://p.scdn.co/mp3-preview/ab12c3d4e5f67890123456789abcdef01234567"
        )
        print(f"نتیجه: {result}")
    else:
        print("❌ Downloader در دسترس نیست - تنظیمات را چک کنید")