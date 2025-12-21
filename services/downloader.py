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
    
    # ==================== دانلود از YouTube ====================
    
    def download_from_youtube(
        self,
        video_id: str = None,
        url: str = None,
        track_name: str = None,
        artist_name: str = None
    ) -> Optional[str]:
        """
        دانلود موزیک از YouTube
        
        Args:
            video_id: شناسه ویدیو YouTube
            url: لینک مستقیم YouTube
            track_name: نام آهنگ (برای جستجو)
            artist_name: نام هنرمند (برای جستجو)
        
        Returns:
            مسیر فایل دانلود شده یا None
        """
        try:
            # اگه video_id یا url نداشتیم، جستجو کن
            if not video_id and not url:
                if not track_name:
                    logger.error("❌ نیاز به video_id، url، یا track_name")
                    return None
                
                video = self.search_youtube(track_name, artist_name or "")
                if not video:
                    return None
                
                video_id = video.get('id')
            
            # ساخت URL
            if not url:
                url = f"https://www.youtube.com/watch?v={video_id}"
            
            logger.info(f"📥 در حال دانلود از: {url}")
            
            # دانلود
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # پیدا کردن فایل دانلود شده
                video_id = info.get('id', 'unknown')
                downloaded_file = self.download_dir / f"{video_id}.mp3"
                
                if downloaded_file.exists():
                    file_size_mb = downloaded_file.stat().st_size / (1024 * 1024)
                    logger.info(f"✅ دانلود موفق: {downloaded_file.name} ({file_size_mb:.2f} MB)")
                    return str(downloaded_file)
                else:
                    logger.error("❌ فایل دانلود شده پیدا نشد")
                    return None
                
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
            return None
    
    # ==================== دانلود با جستجوی خودکار ====================
    
    def download_track(
        self,
        track_name: str,
        artist_name: str,
        max_size_mb: int = None
    ) -> Optional[str]:
        """
        دانلود آهنگ با جستجوی خودکار در YouTube
        
        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند
            max_size_mb: حداکثر حجم مجاز (مگابایت)
        
        Returns:
            مسیر فایل یا None
        """
        if max_size_mb is None:
            max_size_mb = config.MAX_DOWNLOAD_SIZE_MB
        
        logger.info(f"🎵 در حال دانلود: {track_name} - {artist_name}")
        
        # جستجو در YouTube
        video = self.search_youtube(track_name, artist_name)
        if not video:
            logger.warning("⚠️ ویدیو پیدا نشد")
            return None
        
        # بررسی مدت زمان (برای جلوگیری از دانلود چیزهای طولانی)
        duration = video.get('duration', 0)
        if duration > 600:  # بیشتر از 10 دقیقه
            logger.warning(f"⚠️ ویدیو خیلی طولانیه: {duration}s")
            return None
        
        # دانلود
        video_id = video.get('id')
        file_path = self.download_from_youtube(video_id=video_id)
        
        if not file_path:
            return None
        
        # بررسی حجم فایل
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            logger.warning(f"⚠️ فایل خیلی بزرگه: {file_size_mb:.2f} MB")
            # حذف فایل
            Path(file_path).unlink()
            return None
        
        return file_path
    
    # ==================== دانلود با لینک Spotify ====================
    
    def download_from_spotify_info(
        self,
        track_info: Dict[str, Any]
    ) -> Optional[str]:
        """
        دانلود آهنگ با استفاده از اطلاعات Spotify
        
        Args:
            track_info: دیکشنری فرمت شده از spotify service
        
        Returns:
            مسیر فایل یا None
        """
        track_name = track_info.get('name')
        artist_str = track_info.get('artist_str')
        
        if not track_name:
            logger.error("❌ نام آهنگ موجود نیست")
            return None
        
        return self.download_track(track_name, artist_str or "")
    
    # ==================== مدیریت فایل‌ها ====================
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        پاک کردن فایل‌های قدیمی
        
        Args:
            max_age_hours: حداکثر سن فایل به ساعت
        """
        import time
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        try:
            for file in self.download_dir.glob('*'):
                if file.is_file():
                    file_age = now - file.stat().st_mtime
                    if file_age > max_age_seconds:
                        file.unlink()
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"🗑️ {deleted_count} فایل قدیمی حذف شد")
                
        except Exception as e:
            logger.error(f"❌ خطا در cleanup: {e}")
    
    def get_file_size(self, file_path: str) -> float:
        """
        دریافت حجم فایل به مگابایت
        
        Args:
            file_path: مسیر فایل
        
        Returns:
            حجم به MB
        """
        try:
            size_bytes = Path(file_path).stat().st_size
            return size_bytes / (1024 * 1024)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت حجم فایل: {e}")
            return 0
    
    def delete_file(self, file_path: str):
        """
        حذف یک فایل
        
        Args:
            file_path: مسیر فایل
        """
        try:
            Path(file_path).unlink()
            logger.info(f"🗑️ فایل حذف شد: {file_path}")
        except Exception as e:
            logger.error(f"❌ خطا در حذف فایل: {e}")
    
    # ==================== Download with Fallback ====================
    
    def download_with_fallback(
        self,
        track_name: str,
        artist_name: str,
        spotify_preview_url: str = None
    ) -> Optional[str]:
        """
        دانلود با روش‌های جایگزین
        
        اول YouTube رو امتحان می‌کنه
        اگه نشد و preview URL داره، اون رو دانلود می‌کنه
        
        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند
            spotify_preview_url: لینک preview 30 ثانیه‌ای Spotify
        
        Returns:
            مسیر فایل یا None
        """
        # روش 1: YouTube
        file_path = self.download_track(track_name, artist_name)
        
        if file_path:
            return file_path
        
        # روش 2: Spotify Preview (اگه موجود باشه)
        if spotify_preview_url:
            logger.info("⚠️ دانلود از YouTube ناموفق - استفاده از Spotify preview")
            return self._download_spotify_preview(spotify_preview_url, track_name)
        
        logger.error("❌ تمام روش‌های دانلود ناموفق بود")
        return None
    
    def _download_spotify_preview(
        self,
        preview_url: str,
        track_name: str
    ) -> Optional[str]:
        """
        دانلود preview 30 ثانیه‌ای از Spotify
        
        Args:
            preview_url: لینک preview
            track_name: نام آهنگ
        
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
        size = downloader.get_file_size(file_path)
        print(f"✅ دانلود موفق!")
        print(f"   مسیر: {file_path}")
        print(f"   حجم: {size:.2f} MB")
        
        # حذف فایل تست
        # downloader.delete_file(file_path)
    else:
        print("❌ دانلود ناموفق")