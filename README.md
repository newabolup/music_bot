# ربات تلگرام دانلود آهنگ از یوتیوب

## نصب خودکار روی سرور (Ubuntu / Debian)

```bash
git clone <آدرس-مخزن> music_bot
cd music_bot
sudo ./install.sh
```

اسکریپت به ترتیب این کارها را انجام می‌دهد:
1. اگر پروژه گیت است، کد را به‌روز می‌کند (`git pull`)
2. پایتون، pip، ffmpeg و git را نصب می‌کند
3. محیط مجازی `venv` می‌سازد و کتابخانه‌ها را نصب می‌کند
4. توکن ربات را می‌پرسد و فایل `.env` می‌سازد
5. سرویس `music-bot` را در systemd ثبت می‌کند، روشن می‌کند و همیشه در حال اجرا نگه می‌دارد (حتی بعد از ریبوت)

برای نصب بدون پرسش توکن:
```bash
sudo BOT_TOKEN="123456:ABC..." -E ./install.sh
```

### به‌روزرسانی
```bash
cd music_bot
git pull
sudo ./install.sh
```

### دستورات مفید
```bash
sudo systemctl status music-bot        # وضعیت
journalctl -u music-bot -f             # لاگ زنده
sudo systemctl restart music-bot       # ری‌استارت
sudo systemctl stop music-bot          # توقف
```

## نصب دستی (برای توسعه)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # و توکن را در آن بگذارید
python bot.py
```

ffmpeg باید جداگانه نصب باشد. اگر در PATH نیست، مسیر پوشه `bin` آن را در `.env` با `FFMPEG_LOCATION` مشخص کنید.

## نکته
- اگر دانلودها خطا دادند، yt-dlp را به‌روز کنید: `pip install -U yt-dlp` (یا اجرای مجدد `install.sh`)
- استفاده از محتوای یوتیوب باید با قوانین آن سرویس و کپی‌رایت سازگار باشد. این ربات برای استفاده شخصی طراحی شده است.
