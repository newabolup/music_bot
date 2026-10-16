"""تنظیمات برنامه. مقادیر از فایل .env خوانده می‌شوند."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN در فایل .env تنظیم نشده است.")

# حداقل کیفیت ۱۹۲ کیلوبیت‌بر‌ثانیه است
AUDIO_BITRATE: int = max(192, int(os.getenv("AUDIO_BITRATE", "192")))
MAX_TRACKS: int = int(os.getenv("MAX_TRACKS", "50"))
FFMPEG_LOCATION: str | None = os.getenv("FFMPEG_LOCATION") or None

# تاخیر بین ارسال دو فایل (ثانیه)
SEND_DELAY_MIN: float = 2.0
SEND_DELAY_MAX: float = 3.0

# حداکثر زمان دانلود یک آهنگ (ثانیه)
DOWNLOAD_TIMEOUT: int = 300

# محدودیت حجم فایل در Bot API تلگرام (۵۰ مگابایت)
TELEGRAM_MAX_FILE_SIZE: int = 50 * 1024 * 1024
