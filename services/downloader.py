"""
Downloader Service - دانلود فایل موزیک
از YouTube یا منابع دیگر با استفاده از yt-dlp
"""
import os
import logging
import yt_dlp
from pathlib import Path
from typing import Optional, Dict, Any
from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """کلاس دانلود موزیک"""
    
    def __init__(self):
        """راه‌اندازی downloader"""
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        
        # تنظیمات پیش‌فرض yt-dlp
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.download_dir / '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            # برای جلوگیری از خطاهای rate limit
            'socket_timeout': 30,
            'retries': 3,
        }
        
        logger.info("✅ Music Downloader راه‌اندازی شد")
    
    # ==================== جستجو در YouTube ====================
    
    def search_youtube(
        self,
        track_name: str,
        artist_name: str,
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        جستجوی آهنگ در YouTube
        
        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند
            limit: تعداد نتایج
        
        Returns:
            اطلاعات ویدیو یا None
        """
        search_query = f"{artist_name} {track_name} audio"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(f"ytsearch{limit}:{search_query}", download=False)
                
                if 'entries' in result and result['entries']:
                    video = result['entries'][0]
                    logger.info(f"✅ ویدیو پیدا شد: {video.get('title', 'Unknown')}")
                    return video
                
                logger.warning(f"⚠️ هیچ نتیجه‌ای برای '{search_query}' پیدا نشد")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی YouTube: {e}")
            return None

    def download_track(
        self,
        track_name: str,
        artist_name: str
    ) -> Optional[str]:
        """
        دانلود آهنگ از YouTube
        
        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند
        
        Returns:
            مسیر فایل دانلود شده یا None
        """
        video_info = self.search_youtube(track_name, artist_name)
        if not video_info:
            return None
        
        ydl_opts = self.ydl_opts.copy()
        ydl_opts['outtmpl'] = str(self.download_dir / f"{video_info['id']}.%(ext)s")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_info['url']])
            
            file_path = self.download_dir / f"{video_info['id']}.mp3"
            if file_path.exists():
                logger.info(f"✅ دانلود موفق: {file_path}")
                return str(file_path)
            else:
                logger.warning("⚠️ فایل دانلود شده پیدا نشد")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
            return None

    def download_preview_from_spotify(
        self,
        preview_url: str
    ) -> Optional[str]:
        """
        دانلود preview 30 ثانیه‌ای از Spotify
        
        Args:
            preview_url: لینک preview
        
        Returns:
            مسیر فایل یا None
        """
        try:
            import requests
            import hashlib
            
            # ساخت نام فایل
            file_hash = hashlib.md5(preview_url.encode()).hexdigest()[:8]
            file_name = f"preview_{file_hash}.mp3"
            file_path = self.download_dir / file_name
            
            # دانلود
            logger.info(f"📥 در حال دانلود preview از Spotify...")
            response = requests.get(preview_url, timeout=30)
            response.raise_for_status()
            
            # ذخیره
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✅ Preview دانلود شد: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود preview: {e}")
            return None

    def cleanup_old_files(self, max_age_hours: int = 6):
        """
        پاک کردن فایل‌های قدیمی برای مدیریت فضا
        """
        from datetime import datetime, timedelta
        now = datetime.now()
        for file in self.download_dir.iterdir():
            if file.is_file():
                age = now - datetime.fromtimestamp(file.stat().st_mtime)
                if age > timedelta(hours=max_age_hours):
                    file.unlink()
                    logger.info(f"🗑️ فایل قدیمی حذف شد: {file}")

    def download_with_fallback(
        self,
        track_name: str,
        artist_name: str,
        spotify_preview_url: Optional[str] = None
    ) -> Optional[str]:
        """
        دانلود با fallback: اول YouTube، اگر نشد preview Spotify
        """
        file_path = self.download_track(track_name, artist_name)
        if file_path:
            return file_path
        
        if spotify_preview_url:
            return self.download_preview_from_spotify(spotify_preview_url)
        
        return None

# ==================== Singleton Instance ====================

music_downloader = MusicDownloader()


# ==================== Helper Functions ====================

def download_track_safe(
    track_name: str,
    artist_name: str,
    spotify_info: Dict[str, Any] = None
) -> Optional[str]:
    """
    دانلود ایمن با cleanup خودکار
    
    Args:
        track_name: نام آهنگ
        artist_name: نام هنرمند
        spotify_info: اطلاعات اضافی از Spotify
    
    Returns:
        مسیر فایل یا None
    """
    # پاک کردن فایل‌های قدیمی
    music_downloader.cleanup_old_files(max_age_hours=6)
    
    # دانلود
    preview_url = None
    if spotify_info:
        preview_url = spotify_info.get('preview_url')
    
    return music_downloader.download_with_fallback(
        track_name,
        artist_name,
        spotify_preview_url=preview_url
    )


if __name__ == "__main__":
    # تست downloader
    print("🧪 در حال تست Music Downloader...")
    
    downloader = MusicDownloader()
    
    # تست دانلود
    test_track = "Shape of You"
    test_artist = "Ed Sheeran"
    
    print(f"📥 تست دانلود: {test_track} - {test_artist}")
    
    file_path = downloader.download_track(test_track, test_artist)
    
    if file_path:
        size = os.path.getsize(file_path) / (1024 * 1024)
        print(f"✅ دانلود موفق!")
        print(f"   مسیر: {file_path}")
        print(f"   حجم: {size:.2f} MB")
        
        # حذف فایل تست
        # downloader.delete_file(file_path)
    else:
        print("❌ دانلود ناموفق")