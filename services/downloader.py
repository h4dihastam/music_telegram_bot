"""
Music Downloader با yt-dlp مستقیم
"""
import os
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import aiohttp
import aiofiles

from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """دانلودر موزیک با yt-dlp"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
    
    def is_available(self) -> bool:
        """چک کردن yt-dlp"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    async def download_from_youtube_search(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """دانلود از یوتیوب با جستجو"""
        try:
            query = f"{artist_name} {track_name} official audio"
            logger.info(f"🔍 جستجو در یوتیوب: {query}")
            
            # نام فایل خروجی
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_template = str(self.download_dir / f"song_{query_hash}.%(ext)s")
            
            # دستور yt-dlp
            cmd = [
                'yt-dlp',
                f'ytsearch1:{query}',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '--output', output_template,
                '--no-playlist',
                '--quiet',
                '--no-warnings'
            ]
            
            logger.info("📥 شروع دانلود از یوتیوب...")
            
            # اجرای async
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # پیدا کردن فایل دانلود شده
                output_file = self.download_dir / f"song_{query_hash}.mp3"
                if output_file.exists():
                    logger.info("✅ دانلود از یوتیوب موفق بود")
                    return str(output_file)
                
                # جستجوی فایل‌های جدید
                for file in self.download_dir.iterdir():
                    if file.stem.startswith(f"song_{query_hash}"):
                        logger.info(f"✅ فایل پیدا شد: {file.name}")
                        return str(file)
            else:
                logger.error(f"❌ خطای yt-dlp: {stderr.decode()}")
                
        except asyncio.TimeoutError:
            logger.error("❌ تایم‌اوت در دانلود")
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
        
        return None
    
    async def download_preview_from_spotify(self, preview_url: str) -> Optional[str]:
        """دانلود preview 30 ثانیه"""
        try:
            file_hash = hashlib.md5(preview_url.encode()).hexdigest()[:8]
            file_name = f"preview_{file_hash}.mp3"
            file_path = self.download_dir / file_name
            
            if file_path.exists():
                logger.info("✅ Preview از کش")
                return str(file_path)
            
            logger.info("📥 دانلود preview...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(preview_url, timeout=30) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(await response.read())
                        logger.info("✅ Preview دانلود شد")
                        return str(file_path)
                        
        except Exception as e:
            logger.error(f"❌ خطا در دانلود preview: {e}")
        
        return None
    
    def cleanup_old_files(self, max_age_hours: int = 6):
        """پاک‌سازی فایل‌های قدیمی"""
        now = datetime.now()
        deleted = 0
        
        try:
            if not self.download_dir.exists():
                return
            
            for file in self.download_dir.iterdir():
                if file.is_file():
                    age = now - datetime.fromtimestamp(file.stat().st_mtime)
                    if age > timedelta(hours=max_age_hours):
                        try:
                            file.unlink()
                            deleted += 1
                        except:
                            pass
            
            if deleted > 0:
                logger.info(f"🗑️ {deleted} فایل قدیمی پاک شد")
                
        except Exception as e:
            logger.error(f"❌ خطا در cleanup: {e}")


# Singleton
music_downloader = MusicDownloader()


async def download_track_safe_async(
    track_name: str,
    artist_name: str,
    spotify_url: Optional[str] = None,
    preview_url: Optional[str] = None
) -> Optional[str]:
    """دانلود با fallback"""
    
    music_downloader.cleanup_old_files()
    
    # استراتژی 1: دانلود از یوتیوب
    logger.info("🎯 تلاش برای دانلود از یوتیوب...")
    file_path = await music_downloader.download_from_youtube_search(
        track_name, artist_name
    )
    if file_path:
        logger.info("✅ دانلود از یوتیوب موفق")
        return file_path
    
    # استراتژی 2: preview
    if preview_url:
        logger.info("🎯 دانلود preview...")
        file_path = await music_downloader.download_preview_from_spotify(preview_url)
        if file_path:
            logger.warning("⚠️ فقط preview 30 ثانیه")
            return file_path
    
    logger.error("❌ همه روش‌ها شکست خوردند")
    return None


def download_track_safe(
    track_name: str,
    artist_name: str,
    spotify_url: Optional[str] = None,
    preview_url: Optional[str] = None
) -> Optional[str]:
    """Sync wrapper"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            download_track_safe_async(track_name, artist_name, spotify_url, preview_url)
        )
    finally:
        loop.close()