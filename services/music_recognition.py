"""
سرویس تشخیص آهنگ از ویس/ویدیو با ACRCloud
"""
import os
import logging
import asyncio
import hashlib
import hmac
import base64
import time
from typing import Optional, Dict, Any
from pathlib import Path
import aiohttp
import aiofiles

from core.config import config

logger = logging.getLogger(__name__)


class MusicRecognitionService:
    """سرویس تشخیص آهنگ"""
    
    def __init__(self):
        self.access_key = os.getenv('ACRCLOUD_ACCESS_KEY')
        self.access_secret = os.getenv('ACRCLOUD_ACCESS_SECRET')
        self.host = os.getenv('ACRCLOUD_HOST', 'identify-eu-west-1.acrcloud.com')
        self.endpoint = '/v1/identify'
        
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        if not self.access_key or not self.access_secret:
            logger.warning("⚠️ ACRCloud credentials موجود نیست - تشخیص آهنگ غیرفعال است")
            self.enabled = False
        else:
            logger.info("✅ Music Recognition Service راه‌اندازی شد")
            self.enabled = True
    
    def is_available(self) -> bool:
        """بررسی در دسترس بودن سرویس"""
        return self.enabled
    
    def _generate_signature(self, string_to_sign: str) -> str:
        """ساخت signature برای ACRCloud"""
        return base64.b64encode(
            hmac.new(
                self.access_secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha1
            ).digest()
        ).decode('utf-8')
    
    async def recognize_from_file(
        self, 
        file_path: str,
        duration: int = 12
    ) -> Optional[Dict[str, Any]]:
        """
        تشخیص آهنگ از فایل صوتی/تصویری
        
        Args:
            file_path: مسیر فایل
            duration: مدت زمان برای تشخیص (ثانیه)
        
        Returns:
            اطلاعات آهنگ یا None
        """
        if not self.is_available():
            logger.error("❌ ACRCloud در دسترس نیست")
            return None
        
        try:
            # خواندن فایل
            async with aiofiles.open(file_path, 'rb') as f:
                audio_data = await f.read()
            
            # محدود کردن حجم (فقط 1MB اول)
            if len(audio_data) > 1024 * 1024:
                audio_data = audio_data[:1024 * 1024]
            
            # ساخت request
            timestamp = str(int(time.time()))
            string_to_sign = f"POST\n{self.endpoint}\n{self.access_key}\naudio\n1\n{timestamp}"
            signature = self._generate_signature(string_to_sign)
            
            data = aiohttp.FormData()
            data.add_field('sample', audio_data, filename='sample.mp3')
            data.add_field('access_key', self.access_key)
            data.add_field('data_type', 'audio')
            data.add_field('signature_version', '1')
            data.add_field('signature', signature)
            data.add_field('sample_bytes', str(len(audio_data)))
            data.add_field('timestamp', timestamp)
            
            url = f"https://{self.host}{self.endpoint}"
            
            logger.info(f"🔍 در حال تشخیص آهنگ...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"❌ ACRCloud error: {response.status}")
                        return None
                    
                    result = await response.json()
                    
                    # پردازش نتیجه
                    if result.get('status', {}).get('code') == 0:
                        metadata = result.get('metadata', {})
                        music = metadata.get('music', [])
                        
                        if music:
                            track = music[0]
                            
                            # استخراج اطلاعات
                            track_info = {
                                'title': track.get('title'),
                                'artists': [a.get('name') for a in track.get('artists', [])],
                                'album': track.get('album', {}).get('name'),
                                'release_date': track.get('release_date'),
                                'duration_ms': track.get('duration_ms'),
                                'external_ids': track.get('external_ids', {}),
                                'score': track.get('score', 0)
                            }
                            
                            logger.info(f"✅ آهنگ تشخیص داده شد: {track_info['title']} - {', '.join(track_info['artists'])}")
                            return track_info
                    else:
                        logger.warning(f"⚠️ آهنگ تشخیص داده نشد: {result.get('status', {}).get('msg')}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("⏱️ Timeout در تشخیص آهنگ")
            return None
        except Exception as e:
            logger.error(f"❌ خطا در تشخیص آهنگ: {e}", exc_info=True)
            return None
    
    async def download_instagram_video(
        self,
        instagram_url: str
    ) -> Optional[str]:
        """
        دانلود ویدیو از اینستاگرام با yt-dlp
        
        Args:
            instagram_url: لینک اینستاگرام
        
        Returns:
            مسیر فایل دانلود شده یا None
        """
        try:
            # ساخت نام فایل
            url_hash = hashlib.md5(instagram_url.encode()).hexdigest()[:8]
            output_path = self.temp_dir / f"ig_{url_hash}.mp4"
            
            # چک کش
            if output_path.exists():
                logger.info("✅ ویدیو از کش")
                return str(output_path)
            
            logger.info(f"📥 دانلود ویدیو اینستاگرام...")
            
            cmd = [
                'yt-dlp',
                instagram_url,
                '--format', 'best',
                '--output', str(output_path),
                '--no-playlist',
                '--quiet',
                '--no-warnings',
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )
            
            if process.returncode == 0 and output_path.exists():
                logger.info(f"✅ ویدیو دانلود شد: {output_path.name}")
                return str(output_path)
            else:
                error = stderr.decode()[:200] if stderr else "Unknown"
                logger.error(f"❌ دانلود ناموفق: {error}")
                return None
                
        except asyncio.TimeoutError:
            logger.error("⏱️ Timeout در دانلود ویدیو")
            return None
        except Exception as e:
            logger.error(f"❌ خطا در دانلود ویدیو: {e}")
            return None
    
    async def extract_audio_from_video(
        self,
        video_path: str
    ) -> Optional[str]:
        """
        استخراج صدا از ویدیو با FFmpeg
        
        Args:
            video_path: مسیر فایل ویدیو
        
        Returns:
            مسیر فایل صوتی یا None
        """
        try:
            audio_path = Path(video_path).with_suffix('.mp3')
            
            if audio_path.exists():
                return str(audio_path)
            
            logger.info("🎵 استخراج صدا از ویدیو...")
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # بدون ویدیو
                '-acodec', 'libmp3lame',
                '-q:a', '2',
                '-t', '30',  # فقط 30 ثانیه اول
                str(audio_path),
                '-y'  # overwrite
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(
                process.communicate(),
                timeout=30
            )
            
            if process.returncode == 0 and audio_path.exists():
                logger.info("✅ صدا استخراج شد")
                return str(audio_path)
            else:
                logger.error("❌ استخراج صدا ناموفق")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطا در استخراج صدا: {e}")
            return None
    
    async def recognize_from_instagram_link(
        self,
        instagram_url: str
    ) -> Optional[Dict[str, Any]]:
        """
        تشخیص آهنگ از لینک اینستاگرام
        
        Args:
            instagram_url: لینک پست اینستاگرام
        
        Returns:
            اطلاعات آهنگ یا None
        """
        try:
            # 1. دانلود ویدیو
            video_path = await self.download_instagram_video(instagram_url)
            if not video_path:
                return None
            
            # 2. استخراج صدا
            audio_path = await self.extract_audio_from_video(video_path)
            if not audio_path:
                return None
            
            # 3. تشخیص آهنگ
            result = await self.recognize_from_file(audio_path)
            
            # 4. پاک‌سازی
            try:
                os.remove(video_path)
                os.remove(audio_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"❌ خطا در تشخیص از اینستاگرام: {e}")
            return None
    
    def cleanup_temp_files(self, max_age_hours: int = 2):
        """پاک‌سازی فایل‌های موقت قدیمی"""
        from datetime import datetime, timedelta
        
        try:
            if not self.temp_dir.exists():
                return
            
            now = datetime.now()
            deleted = 0
            
            for file in self.temp_dir.iterdir():
                if file.is_file():
                    age = now - datetime.fromtimestamp(file.stat().st_mtime)
                    if age > timedelta(hours=max_age_hours):
                        try:
                            file.unlink()
                            deleted += 1
                        except:
                            pass
            
            if deleted > 0:
                logger.info(f"🗑️ {deleted} فایل موقت پاک شد")
                
        except Exception as e:
            logger.error(f"❌ خطا در cleanup: {e}")


# Singleton
recognition_service = MusicRecognitionService()


# Helper functions
async def recognize_music_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """تابع کمکی برای تشخیص از فایل"""
    return await recognition_service.recognize_from_file(file_path)


async def recognize_music_from_instagram(url: str) -> Optional[Dict[str, Any]]:
    """تابع کمکی برای تشخیص از اینستاگرام"""
    return await recognition_service.recognize_from_instagram_link(url)