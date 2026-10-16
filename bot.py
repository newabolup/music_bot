"""ربات تلگرام: دریافت لیست آهنگ، دانلود و ارسال تک‌تک فایل‌ها."""
import asyncio
import logging
import os
import random
import shutil
import tempfile

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, Message

from config import (
    BOT_TOKEN,
    DOWNLOAD_TIMEOUT,
    MAX_TRACKS,
    SEND_DELAY_MAX,
    SEND_DELAY_MIN,
    TELEGRAM_MAX_FILE_SIZE,
)
from downloader import TrackNotFoundError, download_track
from track_parser import Track, parse_track_list

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("music_bot")

router = Router()

# جلوگیری از اجرای همزمان چند درخواست برای یک چت
_active_chats: set[int] = set()

START_TEXT = (
    "سلام! 🎵\n"
    "لیست آهنگ‌های خود را به این شکل برای من بفرستید:\n\n"
    "1\n"
    "Goth (Slowed + Reverb)\n"
    "Sidewalks and Skeletons\n"
    "2\n"
    "Dark Beach\n"
    "Pastel Ghost\n\n"
    "برای راهنمای کامل /help را بزنید."
)

HELP_TEXT = (
    "📖 راهنما\n\n"
    "هر آهنگ باید سه خط داشته باشد:\n"
    "۱. شماره آهنگ\n"
    "۲. نام آهنگ\n"
    "۳. نام خواننده\n\n"
    f"حداکثر {MAX_TRACKS} آهنگ در هر درخواست پردازش می‌شود.\n"
    "هر آهنگ به صورت MP3 با کیفیت ۱۹۲ کیلوبیت ارسال می‌شود.\n"
    "اگر آهنگی پیدا نشود یا خطا بدهد، به شما اطلاع داده می‌شود و بقیه ادامه می‌یابند."
)


# ---------- دستورات ----------

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


# ---------- دریافت لیست ----------

@router.message(F.text & ~F.text.startswith("/"))
async def handle_playlist(message: Message, bot: Bot) -> None:
    chat_id = message.chat.id

    if chat_id in _active_chats:
        await message.answer("⏳ یک درخواست در حال پردازش است. لطفاً صبر کنید.")
        return

    tracks = parse_track_list(message.text or "")
    if not tracks:
        await message.answer(
            "❌ لیستی پیدا نشد. فرمت را مطابق /help بفرستید."
        )
        return

    if len(tracks) > MAX_TRACKS:
        await message.answer(
            f"⚠️ لیست شما {len(tracks)} آهنگ دارد؛ فقط {MAX_TRACKS} آهنگ اول پردازش می‌شود."
        )
        tracks = tracks[:MAX_TRACKS]

    _active_chats.add(chat_id)
    try:
        await process_tracks(bot, chat_id, tracks)
    except Exception:
        logger.exception("خطای غیرمنتظره در پردازش لیست")
        await bot.send_message(chat_id, "❌ خطای غیرمنتظره‌ای رخ داد.")
    finally:
        _active_chats.discard(chat_id)


# ---------- پردازش اصلی ----------

async def process_tracks(bot: Bot, chat_id: int, tracks: list[Track]) -> None:
    total = len(tracks)
    status = await bot.send_message(chat_id, f"🚀 شروع کار. {total} آهنگ در لیست است.")

    succeeded = 0
    failed: list[str] = []

    for index, track in enumerate(tracks, start=1):
        await _safe_edit(
            status,
            f"⬇️ در حال دانلود آهنگ {index} از {total}:\n{track.display_name}",
        )

        work_dir = tempfile.mkdtemp(prefix="tgmusic_")
        try:
            await _download_and_send(bot, chat_id, track, work_dir, index, total)
            succeeded += 1
            await bot.send_message(
                chat_id, f"✅ آهنگ «{track.display_name}» با موفقیت ارسال شد."
            )
        except TrackNotFoundError:
            failed.append(track.display_name)
            await bot.send_message(
                chat_id, f"🔍 آهنگ «{track.display_name}» در یوتیوب پیدا نشد."
            )
        except asyncio.TimeoutError:
            failed.append(track.display_name)
            await bot.send_message(
                chat_id, f"⏱ دانلود «{track.display_name}» بیش از حد طول کشید."
            )
        except Exception as exc:  # خطاهای دانلود، تبدیل یا ارسال
            logger.exception("خطا در آهنگ %s", track.display_name)
            failed.append(track.display_name)
            await bot.send_message(
                chat_id, f"❌ خطا در «{track.display_name}»: {exc}"
            )
        finally:
            # پاک‌سازی فایل‌های موقت بعد از ارسال (یا شکست)
            shutil.rmtree(work_dir, ignore_errors=True)

        # تاخیر بین ارسال فایل‌ها تا محدودیت تلگرام فعال نشود
        if index < total:
            await asyncio.sleep(random.uniform(SEND_DELAY_MIN, SEND_DELAY_MAX))

    await _safe_edit(status, "🏁 کار تمام شد.")
    summary = f"🏁 کار تموم شد!\n✅ موفق: {succeeded}\n❌ ناموفق: {len(failed)}"
    if failed:
        summary += "\n\nآهنگ‌های ناموفق:\n" + "\n".join(f"• {name}" for name in failed)
    await bot.send_message(chat_id, summary)


async def _download_and_send(
    bot: Bot,
    chat_id: int,
    track: Track,
    work_dir: str,
    index: int,
    total: int,
) -> None:
    mp3_path = await asyncio.wait_for(
        download_track(track.search_query, work_dir),
        timeout=DOWNLOAD_TIMEOUT,
    )

    if os.path.getsize(mp3_path) > TELEGRAM_MAX_FILE_SIZE:
        raise RuntimeError("حجم فایل از ۵۰ مگابایت بیشتر است و تلگرام آن را نمی‌پذیرد.")

    await _send_audio_with_retry(
        bot,
        chat_id,
        mp3_path,
        title=track.title,
        performer=track.artist or None,
        caption=f"{index}/{total}",
    )


async def _send_audio_with_retry(bot: Bot, chat_id: int, path: str, **kwargs) -> None:
    """ارسال فایل؛ اگر تلگرام Flood Limit داد، یک بار دیگر تلاش می‌کند."""
    try:
        await bot.send_audio(chat_id, FSInputFile(path), **kwargs)
    except TelegramRetryAfter as exc:
        logger.warning("Flood limit: %s ثانیه صبر", exc.retry_after)
        await asyncio.sleep(exc.retry_after)
        await bot.send_audio(chat_id, FSInputFile(path), **kwargs)


async def _safe_edit(message: Message, text: str) -> None:
    """ویرایش پیام وضعیت؛ اگر متن تغییری نکرده باشد خطا را نادیده می‌گیرد."""
    try:
        await message.edit_text(text)
    except TelegramBadRequest:
        pass


# ---------- اجرا ----------

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("ربات شروع به کار کرد.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
