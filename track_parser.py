"""پارس کردن لیست آهنگ‌های ارسالی کاربر.

فرمت ورودی:
    1
    Goth (Slowed + Reverb)
    Sidewalks and Skeletons
    2
    Dark Beach
    Pastel Ghost
"""
import re
from dataclasses import dataclass

# خطی که فقط شماره است (مثل "1" یا "2." یا "3)")
_NUMBER_LINE = re.compile(r"^\s*(\d+)\s*[.)]?\s*$")


@dataclass(frozen=True)
class Track:
    position: int  # شماره‌ای که کاربر فرستاده
    title: str
    artist: str

    @property
    def search_query(self) -> str:
        """متن جستجو برای yt-dlp."""
        return f"{self.title} {self.artist}".strip()

    @property
    def display_name(self) -> str:
        return f"{self.title} - {self.artist}" if self.artist else self.title


def parse_track_list(text: str) -> list[Track]:
    """متن کامل پیام را به لیستی از Track تبدیل می‌کند."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    tracks: list[Track] = []

    i = 0
    while i < len(lines):
        match = _NUMBER_LINE.match(lines[i])
        if not match:
            i += 1
            continue

        position = int(match.group(1))

        # خطوط بعد از شماره را تا رسیدن به شماره بعدی یا پر شدن دو فیلد جمع می‌کنیم
        fields: list[str] = []
        j = i + 1
        while j < len(lines) and len(fields) < 2 and not _NUMBER_LINE.match(lines[j]):
            fields.append(lines[j])
            j += 1

        if fields:
            title = fields[0]
            artist = fields[1] if len(fields) > 1 else ""
            tracks.append(Track(position=position, title=title, artist=artist))

        i = j

    return tracks
