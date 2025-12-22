"""
Downloader Service - دانلود فایل موزیک
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
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        
        # تنظیمات yt-dlp با راه‌حل مشکل bot detection
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
            'socket_timeout': 30,
            'retries': 3,
            # اضافه کردن User-Agent برای جلوگیری از bot detection
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # اضافه کردن referer
            'referer': 'https://www.youtube.com/',
            # غیرفعال کردن client-side throttling
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        logger.info("✅ Music Downloader راه‌اندازی شد")
    
    def search_youtube(
        self,
        track_name: str,
        artist_name: str,
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """جستجوی آهنگ در YouTube"""
        search_query = f"{artist_name} {track_name} audio"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(f"ytsearch{limit}:{search_query}", download=False)
                
                if 'entries' in result and result['entries']:
                    video = result['entries'][0]
                    logger.info(f"✅ ویدیو پیدا شد: {video.get('title', 'Unknown')}")
                    return video
                
                logger.warning(f"⚠️ نتیجه‌ای پیدا نشد")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return None

    def download_track(
        self,
        track_name: str,
        artist_name: str
    ) -> Optional[str]:
        """دانلود آهنگ"""
        video_info = self.search_youtube(track_name, artist_name)
        if not video_info:
            logger.warning("⚠️ ویدیو پیدا نشد، از Spotify preview استفاده می‌کنیم")
            return None
        
        ydl_opts = self.ydl_opts.copy()
        ydl_opts['outtmpl'] = str(self.download_dir / f"{video_info['id']}.%(ext)s")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_info['id']}"])
            
            file_path = self.download_dir / f"{video_info['id']}.mp3"
            if file_path.exists():
                logger.info(f"✅ دانلود موفق: {file_path}")
                return str(file_path)
            else:
                logger.warning("⚠️ فایل پیدا نشد")
                return None
                
        except yt_dlp.utils.DownloadError as e:
            if 'Sign in' in str(e) or 'bot' in str(e):
                logger.warning("⚠️ YouTube bot detection - از preview استفاده می‌کنیم")
            else:
                logger.error(f"❌ خطا در دانلود: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
            return None

    def download_preview_from_spotify(
        self,
        preview_url: str
    ) -> Optional[str]:
        """دانلود preview 30 ثانیه از Spotify"""
        try:
            import requests
            import hashlib
            
            file_hash = hashlib.md5(preview_url.encode()).hexdigest()[:8]
            file_name = f"preview_{file_hash}.mp3"
            file_path = self.download_dir / file_name
            
            logger.info(f"📥 در حال دانلود preview از Spotify...")
            response = requests.get(preview_url, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"✅ Preview دانلود شد")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ خطا در دانلود preview: {e}")
            return None

    def cleanup_old_files(self, max_age_hours: int = 6):
        """پاک کردن فایل‌های قدیمی"""
        from datetime import datetime, timedelta
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
                logger.info(f"🗑️ {deleted} فایل قدیمی حذف شد")
        except Exception as e:
            logger.error(f"❌ خطا در cleanup: {e}")

    def download_with_fallback(
        self,
        track_name: str,
        artist_name: str,
        spotify_preview_url: Optional[str] = None
    ) -> Optional[str]:
        """دانلود با fallback"""
        # اول YouTube
        file_path = self.download_track(track_name, artist_name)
        
        if file_path:
            return file_path
        
        # اگر نشد، Spotify preview
        if spotify_preview_url:
            logger.info("⚠️ YouTube ناموفق - استفاده از Spotify preview")
            return self.download_preview_from_spotify(spotify_preview_url)
        
        logger.error("❌ تمام روش‌های دانلود ناموفق")
        return None


# Singleton
music_downloader = MusicDownloader()


def download_track_safe(
    track_name: str,
    artist_name: str,
    spotify_info: Dict[str, Any] = None
) -> Optional[str]:
    """دانلود ایمن با cleanup"""
    music_downloader.cleanup_old_files(max_age_hours=6)
    
    preview_url = None
    if spotify_info:
        preview_url = spotify_info.get('preview_url')
    
    return music_downloader.download_with_fallback(
        track_name,
        artist_name,
        spotify_preview_url=preview_url
    )