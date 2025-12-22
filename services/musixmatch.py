"""
Musixmatch Service - دریافت متن (lyrics) آهنگ با استفاده از API غیررسمی رایگان
منبع: https://github.com/Strvm/musicxmatch-api
"""
import logging
import requests
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# آدرس API غیررسمی رایگان (بدون نیاز به کلید)
BASE_URL = "https://api.music.xiaomiir.com/api/v2/music/lyrics"

class MusixmatchService:
    """کلاس برای دریافت lyrics از سرویس رایگان"""

    def __init__(self):
        logger.info("✅ Musixmatch Service (غیررسمی رایگان) راه‌اندازی شد")

    def search_lyrics(self, track_name: str, artist_name: str) -> Optional[str]:
        """
        جستجو و دریافت lyrics با نام آهنگ و هنرمند

        Args:
            track_name: نام آهنگ
            artist_name: نام هنرمند

        Returns:
            متن کامل آهنگ یا None
        """
        try:
            # ساخت query
            query = f"{track_name} {artist_name}"
            encoded_query = quote(query)

            url = f"{BASE_URL}?query={encoded_query}"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ پاسخ ناموفق از API: {response.status_code}")
                return None

            data = response.json()

            # چک کردن وجود نتیجه
            if not data or 'lyrics' not in data:
                logger.info(f"ℹ️ lyrics پیدا نشد برای: {track_name} - {artist_name}")
                return None

            lyrics = data['lyrics'].strip()

            if not lyrics or lyrics == "Not found":
                return None

            logger.info(f"✅ lyrics دریافت شد برای: {track_name} - {artist_name}")
            return lyrics

        except requests.exceptions.Timeout:
            logger.error("⏰ تایم‌اوت در دریافت lyrics")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ خطا در ارتباط با API غیررسمی: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ خطای غیرمنتظره در دریافت lyrics: {e}")
            return None

    def format_lyrics_for_message(self, lyrics: str, max_length: int = 1000) -> str:
        """
        فرمت کردن lyrics برای نمایش در تلگرام
        """
        if not lyrics:
            return "❌ متن آهنگ در دسترس نیست"

        if len(lyrics) > max_length:
            lyrics = lyrics[:max_length]
            last_newline = lyrics.rfind('\n')
            if last_newline > 0:
                lyrics = lyrics[:last_newline]
            lyrics += "\n\n... (متن کامل در دسترس نیست)"

        return f"📝 متن آهنگ:\n\n{lyrics}"


# ==================== Singleton Instance ====================

musixmatch_service = MusixmatchService()


# ==================== Helper Function ====================

def get_track_lyrics(
    track_name: str,
    artist_name: str,
    spotify_id: str = None,
    use_cache: bool = False  # فعلاً cache نداریم، ولی ساختار نگه داشته شد
) -> Optional[str]:
    """
    دریافت lyrics با نام آهنگ و هنرمند
    """
    return musixmatch_service.search_lyrics(track_name, artist_name)


if __name__ == "__main__":
    print("🧪 تست Musixmatch غیررسمی...")
    lyrics = musixmatch_service.search_lyrics("Shape of You", "Ed Sheeran")
    if lyrics:
        print("\n📝 بخشی از متن:")
        print(lyrics[:300] + "..." if len(lyrics) > 300 else lyrics)
    else:
        print("❌ متن پیدا نشد")