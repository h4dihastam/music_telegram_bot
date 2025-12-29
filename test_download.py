#!/usr/bin/env python3
"""
اسکریپت تست دانلود - برای دیباگ
"""
import asyncio
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_download():
    """تست دانلود"""
    print("="*60)
    print("🧪 تست سیستم دانلود")
    print("="*60)
    
    # 1. چک yt-dlp
    print("\n1️⃣ چک کردن yt-dlp...")
    try:
        import subprocess
        result = subprocess.run(['yt-dlp', '--version'], 
                              capture_output=True, 
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            print(f"   ✅ yt-dlp version: {result.stdout.strip()}")
        else:
            print(f"   ❌ yt-dlp کار نمی‌کنه")
            return False
    except Exception as e:
        print(f"   ❌ خطا: {e}")
        return False
    
    # 2. چک FFmpeg
    print("\n2️⃣ چک کردن FFmpeg...")
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"   ✅ {version_line}")
        else:
            print(f"   ❌ FFmpeg کار نمی‌کنه")
            return False
    except Exception as e:
        print(f"   ❌ خطا: {e}")
        return False
    
    # 3. تست دانلود واقعی
    print("\n3️⃣ تست دانلود از YouTube...")
    try:
        from services.downloader import download_track_safe_async
        
        result = await download_track_safe_async(
            track_name="Blinding Lights",
            artist_name="The Weeknd"
        )
        
        if result and os.path.exists(result):
            file_size = os.path.getsize(result)
            print(f"   ✅ دانلود موفق!")
            print(f"   📁 فایل: {result}")
            print(f"   📊 حجم: {file_size/1024/1024:.1f}MB")
            
            # پاک کردن فایل تست
            try:
                os.remove(result)
                print(f"   🗑️ فایل تست پاک شد")
            except:
                pass
            
            return True
        else:
            print(f"   ❌ دانلود ناموفق")
            return False
            
    except Exception as e:
        print(f"   ❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*60)


if __name__ == "__main__":
    result = asyncio.run(test_download())
    
    if result:
        print("\n✅ همه چیز OK!")
        sys.exit(0)
    else:
        print("\n❌ مشکل وجود داره!")
        sys.exit(1)