"""
Music Downloader - نسخه قوی‌تر با retry و fallback بهتر
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
    """دانلودر موزیک از چند منبع - نسخه بهبود یافته"""
    
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.download_dir.mkdir(exist_ok=True)
        self._check_ytdlp()
        logger.info("✅ Downloader راه‌اندازی شد")
    
    def _check_ytdlp(self):
        """چک کردن نصب بودن yt-dlp"""
        try:
            import subprocess
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                logger.info(f"✅ yt-dlp version: {result.stdout.strip()}")
            else:
                logger.warning("⚠️ yt-dlp نصب نیست یا کار نمی‌کنه")
        except Exception as e:
            logger.error(f"❌ مشکل در yt-dlp: {e}")
    
    async def download_from_youtube(
        self,
        track_name: str,
        artist_name: str,
        retries: int = 2
    ) -> Optional[str]:
        """دانلود از YouTube با retry"""
        
        # جستجوهای مختلف
        search_queries = [
            f"{artist_name} {track_name} official audio",
            f"{artist_name} {track_name}",
            f"{track_name} {artist_name} audio",
        ]
        
        for attempt, query in enumerate(search_queries, 1):
            logger.info(f"🔍 YouTube (تلاش {attempt}/{len(search_queries)}): '{query}'")
            
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
                '--socket-timeout', '20',
                '--retries', '3',
            ]
            
            try:
                logger.info("📥 دانلود از YouTube...")
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60  # 60 ثانیه
                )
                
                if process.returncode == 0:
                    # پیدا کردن فایل
                    for file in self.download_dir.iterdir():
                        if file.stem.startswith(f"yt_{query_hash}") and file.suffix == '.mp3':
                            file_size = file.stat().st_size
                            logger.info(f"✅ YouTube موفق: {file.name} ({file_size/1024/1024:.1f}MB)")
                            return str(file)
                else:
                    error = stderr.decode()[:200] if stderr else "Unknown"
                    logger.debug(f"⚠️ YouTube ناموفق: {error}")
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ YouTube timeout برای '{query}'")
                try:
                    process.kill()
                except:
                    pass
                continue
            except Exception as e:
                logger.error(f"❌ YouTube error: {e}")
                continue
        
        logger.warning("❌ YouTube: همه تلاش‌ها ناموفق")
        return None
    
    async def download_from_soundcloud(
        self, 
        track_name: str, 
        artist_name: str
    ) -> Optional[str]:
        """دانلود از SoundCloud"""
        search_queries = [
            f"{artist_name} {track_name}",
            f"{track_name} {artist_name}",
        ]
        
        for query in search_queries:
            logger.info(f"🔍 SoundCloud: '{query}'")
            
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_template = str(self.download_dir / f"sc_{query_hash}.%(ext)s")
            
            # بررسی کش
            for file in self.download_dir.iterdir():
                if file.stem.startswith(f"sc_{query_hash}") and file.suffix == '.mp3':
                    logger.info(f"✅ از کش: {file.name}")
                    return str(file)
            
            cmd = [
                'yt-dlp',
                f'scsearch1:{query}',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '--output', output_template,
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                '--no-check-certificates',
                '--socket-timeout', '20',
                '--retries', '2',
            ]
            
            try:
                logger.info("📥 دانلود از SoundCloud...")
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60
                )
                
                if process.returncode == 0:
                    for file in self.download_dir.iterdir():
                        if file.stem.startswith(f"sc_{query_hash}") and file.suffix == '.mp3':
                            logger.info(f"✅ SoundCloud موفق: {file.name}")
                            return str(file)
                else:
                    logger.debug(f"⚠️ SoundCloud ناموفق")
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ SoundCloud timeout")
                try:
                    process.kill()
                except:
                    pass
                continue
            except Exception as e:
                logger.error(f"❌ SoundCloud error: {e}")
                continue
        
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
            
            logger.info("📥 دانلود Spotify Preview...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(preview_url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        if len(content) > 0:
                            async with aiofiles.open(file_path, 'wb') as f:
                                await f.write(content)
                            logger.info(f"✅ Preview دانلود شد ({len(content)/1024:.0f}KB)")
                            return str(file_path)
                        
        except Exception as e:
            logger.error(f"❌ خطا در دانلود preview: {e}")
        
        return None
    
    def cleanup_old_files(self, max_age_hours: int = 3):
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
    دانلود با استراتژی چندگانه:
    1. YouTube (بهترین شانس)
    2. SoundCloud
    3. Spotify Preview
    """
    
    # پاکسازی
    music_downloader.cleanup_old_files(max_age_hours=2)
    
    logger.info(f"🎵 شروع دانلود: {track_name} - {artist_name}")
    
    # استراتژی 1: YouTube (شانس بیشتر)
    logger.info("🎯 استراتژی 1/3: YouTube")
    file_path = await music_downloader.download_from_youtube(
        track_name, artist_name
    )
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size > 100000:  # بیشتر از 100KB
            logger.info(f"✅ YouTube موفق: {os.path.basename(file_path)}")
            return file_path
        else:
            logger.warning(f"⚠️ فایل خیلی کوچیکه ({file_size} bytes), حذف میشه")
            try:
                os.remove(file_path)
            except:
                pass
    
    # استراتژی 2: SoundCloud
    logger.info("🎯 استراتژی 2/3: SoundCloud")
    file_path = await music_downloader.download_from_soundcloud(
        track_name, artist_name
    )
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size > 100000:
            logger.info(f"✅ SoundCloud موفق: {os.path.basename(file_path)}")
            return file_path
    
    # استراتژی 3: Preview (آخرین راه)
    if preview_url:
        logger.info("🎯 استراتژی 3/3: Spotify Preview")
        file_path = await music_downloader.download_preview_from_spotify(preview_url)
        if file_path and os.path.exists(file_path):
            logger.warning("⚠️ فقط Preview 30 ثانیه")
            return file_path
    
    logger.error("❌ همه روش‌ها شکست خوردند")
    return None


# تست
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("🧪 تست Downloader...")
        
        # تست
        result = await download_track_safe_async(
            "Blinding Lights",
            "The Weeknd"
        )
        
        if result:
            print(f"✅ دانلود موفق: {result}")
            print(f"   حجم: {os.path.getsize(result)/1024/1024:.1f}MB")
        else:
            print("❌ دانلود ناموفق")
    
    asyncio.run(test())