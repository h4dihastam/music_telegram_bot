"""
Music Downloader با spotDL - نسخه اصلاح شده با async
"""
import os
import logging
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import subprocess
import tempfile

from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """دانلودر موزیک با استفاده از spotDL در subprocess"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
    
    def is_available(self) -> bool:
        """چک کردن در دسترس بودن spotDL"""
        try:
            import spotdl
            return True
        except ImportError:
            logger.warning("⚠️ spotDL نصب نیست")
            return False
    
    async def download_from_spotify_url(self, spotify_url: str) -> Optional[str]:
        """
        دانلود مستقیم از لینک Spotify با استفاده از subprocess
        """
        try:
            logger.info(f"📥 دانلود از Spotify: {spotify_url}")
            
            # ایجاد نام فایل خروجی
            import hashlib
            url_hash = hashlib.md5(spotify_url.encode()).hexdigest()[:8]
            output_file = self.download_dir / f"song_{url_hash}.mp3"
            
            # استفاده از spotDL در subprocess برای جلوگیری از تداخل event loop
            cmd = [
                "spotdl", "download",
                spotify_url,
                "--output", str(output_file),
                "--format", "mp3",
                "--bitrate", "320k"
            ]
            
            # اضافه کردن credentials اگر موجود باشد
            if config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
                cmd.extend([
                    "--client-id", config.SPOTIFY_CLIENT_ID,
                    "--client-secret", config.SPOTIFY_CLIENT_SECRET
                ])
            
            logger.info(f"🚀 اجرای دستور: {' '.join(cmd)}")
            
            # اجرای فرآیند
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("✅ دانلود با موفقیت انجام شد")
                
                # یافتن فایل دانلود شده
                if output_file.exists():
                    return str(output_file)
                
                # جستجو برای فایل جدید در پوشه دانلود
                for file in self.download_dir.iterdir():
                    if file.suffix in ['.mp3', '.m4a', '.webm']:
                        # اگر فایل جدیدی پیدا شد
                        file_age = datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)
                        if file_age < timedelta(minutes=5):
                            logger.info(f"✅ فایل پیدا شد: {file.name}")
                            return str(file)
            else:
                logger.error(f"❌ خطا در spotDL: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"❌ خطا در دانلود از Spotify: {e}")
        
        return None
    
    async def download_by_search(self, track_name: str, artist_name: str) -> Optional[str]:
        """
        دانلود با جستجو
        """
        try:
            query = f"{artist_name} - {track_name}"
            logger.info(f"🔍 جستجو و دانلود: {query}")
            
            # ایجاد نام فایل
            import hashlib
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_file = self.download_dir / f"song_{query_hash}.mp3"
            
            # استفاده از spotDL برای جستجو
            cmd = [
                "spotdl", "download",
                f"{query}",
                "--output", str(output_file),
                "--format", "mp3"
            ]
            
            if config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
                cmd.extend([
                    "--client-id", config.SPOTIFY_CLIENT_ID,
                    "--client-secret", config.SPOTIFY_CLIENT_SECRET
                ])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                if output_file.exists():
                    return str(output_file)
                
                # جستجوی فایل جدید
                for file in self.download_dir.iterdir():
                    if file.suffix in ['.mp3', '.m4a']:
                        file_age = datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)
                        if file_age < timedelta(minutes=5):
                            return str(file)
            else:
                logger.warning(f"⚠️ جستجو ناموفق: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
        
        return None
    
    async def download_preview_from_spotify(self, preview_url: str) -> Optional[str]:
        """دانلود preview 30 ثانیه"""
        try:
            import aiofiles
            import hashlib
            
            # نام فایل
            url_hash = hashlib.md5(preview_url.encode()).hexdigest()[:8]
            file_name = f"preview_{url_hash}.mp3"
            file_path = self.download_dir / file_name
            
            # اگر قبلاً دانلود شده
            if file_path.exists():
                logger.info(f"✅ Preview از کش بازیابی شد")
                return str(file_path)
            
            logger.info("📥 دانلود preview از Spotify...")
            
            # دانلود async
            async with aiohttp.ClientSession() as session:
                async with session.get(preview_url, timeout=30) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(await response.read())
                        logger.info("✅ Preview دانلود شد")
                        return str(file_path)
                    else:
                        logger.error(f"❌ خطا در دریافت preview: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("❌ تایم‌اوت در دانلود preview")
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
                    # پاک کردن فایل‌های قدیمی
                    if file.name.startswith('preview_') or file.name.startswith('song_'):
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


async def download_track_safe_async(
    track_name: str,
    artist_name: str,
    spotify_url: Optional[str] = None,
    preview_url: Optional[str] = None
) -> Optional[str]:
    """
    دانلود ایمن با چند سطح fallback (نسخه async)
    Returns: مسیر فایل دانلود شده یا None
    """
    
    # پاک‌سازی فایل‌های قدیمی
    music_downloader.cleanup_old_files()
    
    # استراتژی ۱: دانلود از Spotify URL
    if spotify_url:
        logger.info("🎯 تلاش برای دانلود از Spotify URL...")
        file_path = await music_downloader.download_from_spotify_url(spotify_url)
        if file_path:
            logger.info("✅ دانلود از Spotify URL موفق بود")
            return file_path
    
    # استراتژی ۲: دانلود با جستجو
    logger.info("🎯 تلاش برای دانلود با جستجو...")
    file_path = await music_downloader.download_by_search(track_name, artist_name)
    if file_path:
        logger.info("✅ دانلود با جستجو موفق بود")
        return file_path
    
    # استراتژی ۳: دانلود preview (30 ثانیه)
    if preview_url:
        logger.info("🎯 تلاش برای دانلود preview...")
        file_path = await music_downloader.download_preview_from_spotify(preview_url)
        if file_path:
            logger.warning("⚠️ فقط preview 30 ثانیه‌ای دانلود شد")
            return file_path
    
    logger.error("❌ تمام روش‌های دانلود شکست خورد")
    return None


# نسخه sync برای compatibility با کدهای قدیمی
def download_track_safe(
    track_name: str,
    artist_name: str,
    spotify_url: Optional[str] = None,
    preview_url: Optional[str] = None
) -> Optional[str]:
    """
    wrapper برای سازگاری با کدهای sync
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            download_track_safe_async(track_name, artist_name, spotify_url, preview_url)
        )
    finally:
        loop.close()


# تست ساده
if __name__ == "__main__":
    print("🧪 تست Music Downloader...")
    
    # تنظیم logging
    logging.basicConfig(level=logging.INFO)
    
    # تست دانلود preview
    import asyncio
    loop = asyncio.new_event_loop()
    
    async def test():
        result = await download_track_safe_async(
            "Test Song",
            "Test Artist",
            preview_url="https://p.scdn.co/mp3-preview/ab12c3d4e5f67890123456789abcdef01234567"
        )
        print(f"نتیجه: {result}")
    
    loop.run_until_complete(test())