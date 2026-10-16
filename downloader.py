"""جستجو و دانلود آهنگ از یوتیوب با yt-dlp و تبدیل به MP3 با ffmpeg."""
import asyncio
import os

import yt_dlp

from config import AUDIO_BITRATE, FFMPEG_LOCATION


class TrackNotFoundError(Exception):
    """برای آهنگی که در یوتیوب پیدا نشد."""


def _build_options(out_dir: str) -> dict:
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(AUDIO_BITRATE),
            }
        ],
    }
    if FFMPEG_LOCATION:
        opts["ffmpeg_location"] = FFMPEG_LOCATION
    return opts


def _download_sync(query: str, out_dir: str) -> str:
    """نسخه همزمان (blocking). در thread جدا اجرا می‌شود."""
    with yt_dlp.YoutubeDL(_build_options(out_dir)) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)

        entries = [e for e in (info or {}).get("entries", []) if e]
        if not entries:
            raise TrackNotFoundError(query)

        entry = entries[0]
        base_path = os.path.splitext(ydl.prepare_filename(entry))[0]

    mp3_path = base_path + ".mp3"
    if not os.path.exists(mp3_path):
        raise RuntimeError("فایل MP3 بعد از تبدیل پیدا نشد. ffmpeg را بررسی کنید.")
    return mp3_path


async def download_track(query: str, out_dir: str) -> str:
    """آهنگ را دانلود کرده و مسیر فایل MP3 را برمی‌گرداند."""
    return await asyncio.to_thread(_download_sync, query, out_dir)
