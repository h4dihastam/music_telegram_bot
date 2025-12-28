"""
Music Downloader - با SoundCloud بهبود یافته
"""
import os
import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import aiohttp
import aiofiles

from core.config import config

logger = logging.getLogger(__name__)


class MusicDownloader:
    """دانلودر موزیک از چند منبع با اولویت SoundCloud"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        logger.info("✅ Downloader راه‌اندازی شد")
    
    async def download_from_soundcloud(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """دانلود از SoundCloud با yt-dlp - بهبود یافته"""
        try:
            # جستجوهای مختلف برای افزایش شانس پیدا کردن
            search_queries = [
                f"{artist_name} {track_name}",
                f"{track_name} {artist_name}",
                f"{artist_name} - {track_name}",
            ]
            
            for query in search_queries:
                logger.info(f"🔍 SoundCloud: جستجو '{query}'")
                
                query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
                output_template = str(self.download_dir / f"sc_{query_hash}.%(ext)s")
                
                # بررسی کش
                for file in self.download_dir.iterdir():
                    if file.stem.startswith(f"sc_{query_hash}") and file.suffix == '.mp3':
                        logger.info(f"✅ از کش: {file.name}")
                        return str(file)
                
                # دستور yt-dlp برای SoundCloud
                cmd = [
                    'yt-dlp',
                    f'scsearch3:{query}',  # 3 نتیجه اول
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',
                    '--output', output_template,
                    '--no-playlist',
                    '--quiet',
                    '--no-warnings',
                    '--no-check-certificates',
                    '--max-downloads', '1',  # فقط اولین نتیجه
                    '--socket-timeout', '30',
                ]
                
                logger.info("📥 دانلود از SoundCloud...")
                
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
                    logger.warning(f"⏱️ تایم‌اوت برای '{query}'")
                    continue
                
                if process.returncode == 0:
                    # پیدا کردن فایل دانلود شده
                    for file in self.download_dir.iterdir():
                        if file.stem.startswith(f"sc_{query_hash}") and file.suffix == '.mp3':
                            logger.info(f"✅ SoundCloud موفق: {file.name}")
                            return str(file)
                else:
                    logger.debug(f"⚠️ SoundCloud ناموفق برای '{query}'")
                    continue
            
            logger.warning("❌ SoundCloud: هیچ نتیجه‌ای پیدا نشد")
            
        except Exception as e:
            logger.error(f"❌ خطا در SoundCloud: {e}")
        
        return None
    
    async def download_from_youtube(
        self,
        track_name: str,
        artist_name: str
    ) -> Optional[str]:
        """دانلود از YouTube"""
        try:
            query = f"{artist_name} {track_name} official audio"
            logger.info(f"🔍 YouTube: '{query}'")
            
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_template = str(self.download_dir / f"yt_{query_hash}.%(ext)s")
            
            # بررسی کش
            for file in self.download_dir.iterdir():
                if file.stem.startswith(f"yt_{query_hash}") and file.suffix == '.mp3':
                    logger.info(f"✅ از کش: {file.name}")
                    return str(file)
            
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
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                '--socket-timeout', '30',
            ]
            
            logger.info("📥 دانلود از YouTube...")
            
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
                logger.warning("⏱️ YouTube تایم‌اوت")
                return None
            
            if process.returncode == 0:
                for file in self.download_dir.iterdir():
                    if file.stem.startswith(f"yt_{query_hash}") and file.suffix == '.mp3':
                        logger.info(f"✅ YouTube موفق: {file.name}")
                        return str(file)
                        
        except Exception as e:
            logger.error(f"❌ YouTube: {e}")
        
        return None
    
    async def download_preview_from_spotify(self, preview_url: str) -> Optional[str]:
        """دانلود preview 30 ثانیه از Spotify (آخرین گزینه)"""
        try:
            file_hash = hashlib.md5(preview_url.encode()).hexdigest()[:8]
            file_name = f"preview_{file_hash}.mp3"
            file_path = self.download_dir / file_name
            
            if file_path.exists():
                logger.info("✅ Preview از کش")
                return str(file_path)
            
            logger.info("📥 دانلود Spotify Preview (30s)...")
            
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
                if file.is_file() and file.suffix == '.mp3':
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
    دانلود با استراتژی بهینه:
    1. SoundCloud (بهترین کیفیت + کامل)
    2. YouTube (معمولاً موفق)
    3. Spotify Preview (30 ثانیه - آخرین راه)
    
    Returns:
        مسیر فایل یا None
    """
    
    # پاکسازی فایل‌های قدیمی
    music_downloader.cleanup_old_files(max_age_hours=3)
    
    logger.info(f"🎵 شروع دانلود: {track_name} - {artist_name}")
    
    # استراتژی 1: SoundCloud (اولویت اول)
    logger.info("🎯 استراتژی 1/3: SoundCloud")
    file_path = await music_downloader.download_from_soundcloud(
        track_name, artist_name
    )
    if file_path and os.path.exists(file_path):
        logger.info(f"✅ موفق از SoundCloud: {os.path.basename(file_path)}")
        return file_path
    
    # استراتژی 2: YouTube
    logger.info("🎯 استراتژی 2/3: YouTube")
    file_path = await music_downloader.download_from_youtube(
        track_name, artist_name
    )
    if file_path and os.path.exists(file_path):
        logger.info(f"✅ موفق از YouTube: {os.path.basename(file_path)}")
        return file_path
    
    # استراتژی 3: Spotify Preview (آخرین راه - فقط 30 ثانیه)
    if preview_url:
        logger.info("🎯 استراتژی 3/3: Spotify Preview")
        file_path = await music_downloader.download_preview_from_spotify(preview_url)
        if file_path and os.path.exists(file_path):
            logger.warning("⚠️ فقط Preview 30 ثانیه موجود بود")
            return file_path
    
    logger.error("❌ همه روش‌های دانلود شکست خوردند")
    return None


# تست
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("🧪 تست Downloader...")
        
        # تست SoundCloud
        result = await download_track_safe_async(
            "Blinding Lights",
            "The Weeknd"
        )
        
        if result:
            print(f"✅ دانلود موفق: {result}")
        else:
            print("❌ دانلود ناموفق")
    
    asyncio.run(test())