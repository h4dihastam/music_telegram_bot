"""
Music Downloader - با چند منبع
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
import re

from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """دانلودر موزیک از چند منبع"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        logger.info("✅ Downloader راه‌اندازی شد")
    
    async def download_from_soundcloud(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """دانلود از SoundCloud با yt-dlp"""
        try:
            query = f"{artist_name} {track_name}"
            logger.info(f"🔍 جستجو در SoundCloud: {query}")
            
            # نام فایل خروجی
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_template = str(self.download_dir / f"sc_{query_hash}.%(ext)s")
            
            # دستور yt-dlp برای SoundCloud
            cmd = [
                'yt-dlp',
                f'scsearch1:{query}',  # جستجو در SoundCloud
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '--output', output_template,
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                '--no-check-certificates'
            ]
            
            logger.info("📥 دانلود از SoundCloud...")
            
            # اجرای async با timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60  # 60 ثانیه تایم‌اوت
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.error("❌ تایم‌اوت دانلود از SoundCloud")
                return None
            
            if process.returncode == 0:
                # پیدا کردن فایل دانلود شده
                for file in self.download_dir.iterdir():
                    if file.stem.startswith(f"sc_{query_hash}"):
                        logger.info(f"✅ دانلود از SoundCloud موفق: {file.name}")
                        return str(file)
            else:
                error_msg = stderr.decode()[:200]
                logger.warning(f"⚠️ SoundCloud ناموفق: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ خطا در دانلود از SoundCloud: {e}")
        
        return None
    
    async def download_from_generic_search(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """جستجو و دانلود از منابع عمومی (بدون YouTube)"""
        try:
            query = f"{artist_name} {track_name}"
            logger.info(f"🔍 جستجوی عمومی: {query}")
            
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_template = str(self.download_dir / f"gen_{query_hash}.%(ext)s")
            
            # yt-dlp می‌تونه از سایت‌های مختلف دانلود کنه
            cmd = [
                'yt-dlp',
                '--default-search', 'ytsearch',  # fallback
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '--output', output_template,
                '--max-downloads', '1',
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                '--no-check-certificates',
                '--geo-bypass',  # دور زدن محدودیت جغرافیایی
                f'{query} audio'
            ]
            
            logger.info("📥 دانلود از منابع عمومی...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.error("❌ تایم‌اوت")
                return None
            
            if process.returncode == 0:
                for file in self.download_dir.iterdir():
                    if file.stem.startswith(f"gen_{query_hash}"):
                        logger.info(f"✅ دانلود موفق: {file.name}")
                        return str(file)
                        
        except Exception as e:
            logger.error(f"❌ خطا در دانلود: {e}")
        
        return None
    
    async def download_from_alternative_youtube(
        self,
        track_name: str,
        artist_name: str
    ) -> Optional[str]:
        """دانلود از YouTube با proxy و تنظیمات بیشتر"""
        try:
            query = f"{artist_name} {track_name} audio"
            logger.info(f"🔍 YouTube (تنظیمات پیشرفته): {query}")
            
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_template = str(self.download_dir / f"yt_{query_hash}.%(ext)s")
            
            cmd = [
                'yt-dlp',
                f'ytsearch1:{query}',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '--output', output_template,
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                '--no-check-certificates',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--extractor-retries', '3',
                '--geo-bypass',
                '--force-ipv4'
            ]
            
            logger.info("📥 تلاش دانلود از YouTube...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=45
                )
            except asyncio.TimeoutError:
                process.kill()
                return None
            
            if process.returncode == 0:
                for file in self.download_dir.iterdir():
                    if file.stem.startswith(f"yt_{query_hash}"):
                        logger.info(f"✅ YouTube موفق شد")
                        return str(file)
                        
        except Exception as e:
            logger.error(f"❌ YouTube: {e}")
        
        return None
    
    async def download_preview_from_spotify(self, preview_url: str) -> Optional[str]:
        """دانلود preview 30 ثانیه از Spotify"""
        try:
            file_hash = hashlib.md5(preview_url.encode()).hexdigest()[:8]
            file_name = f"preview_{file_hash}.mp3"
            file_path = self.download_dir / file_name
            
            if file_path.exists():
                logger.info("✅ Preview از کش")
                return str(file_path)
            
            logger.info("📥 دانلود Spotify Preview...")
            
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
    """
    دانلود با چند سطح fallback:
    1. SoundCloud
    2. YouTube (با تنظیمات پیشرفته)
    3. منابع عمومی
    4. Spotify Preview
    """
    
    music_downloader.cleanup_old_files()
    
    # استراتژی 1: SoundCloud (بهترین گزینه)
    logger.info("🎯 استراتژی 1: SoundCloud")
    file_path = await music_downloader.download_from_soundcloud(
        track_name, artist_name
    )
    if file_path:
        logger.info("✅ دانلود از SoundCloud موفق")
        return file_path
    
    # استراتژی 2: YouTube با تنظیمات پیشرفته
    logger.info("🎯 استراتژی 2: YouTube پیشرفته")
    file_path = await music_downloader.download_from_alternative_youtube(
        track_name, artist_name
    )
    if file_path:
        logger.info("✅ دانلود از YouTube موفق")
        return file_path
    
    # استراتژی 3: منابع عمومی
    logger.info("🎯 استراتژی 3: منابع عمومی")
    file_path = await music_downloader.download_from_generic_search(
        track_name, artist_name
    )
    if file_path:
        logger.info("✅ دانلود از منابع عمومی موفق")
        return file_path
    
    # استراتژی 4: Spotify Preview (آخرین راه)
    if preview_url:
        logger.info("🎯 استراتژی 4: Spotify Preview")
        file_path = await music_downloader.download_preview_from_spotify(preview_url)
        if file_path:
            logger.warning("⚠️ فقط Preview 30 ثانیه")
            return file_path
    
    logger.error("❌ همه روش‌های دانلود شکست خوردند")
    return None