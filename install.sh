#!/usr/bin/env bash
# نصب خودکار ربات روی سرور لینوکس (Ubuntu / Debian)
#
# استفاده:
#   sudo ./install.sh
#   یا بدون پرسش توکن:  sudo BOT_TOKEN="123:ABC" -E ./install.sh
#
# اگر پروژه با گیت کلون شده باشد، قبل از نصب، کد به‌روز می‌شود (git pull).
# اجرای مجدد همین اسکریپت = به‌روزرسانی و ری‌استارت ربات.

set -euo pipefail

APP_NAME="music-bot"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
ENV_FILE="${APP_DIR}/.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }

# ---------- بررسی‌های اولیه ----------

if [[ $EUID -ne 0 ]]; then
    die "این اسکریپت باید با root یا sudo اجرا شود: sudo ./install.sh"
fi

command -v apt-get >/dev/null 2>&1 || die "این اسکریپت فقط برای Ubuntu/Debian است."

# کاربری که ربات با آن اجرا می‌شود (کاربری که sudo را زده)
RUN_USER="${SUDO_USER:-root}"
info "پوشه پروژه: ${APP_DIR}"
info "کاربر اجرای ربات: ${RUN_USER}"

# ---------- به‌روزرسانی کد از گیت ----------

if [[ -d "${APP_DIR}/.git" ]]; then
    info "به‌روزرسانی کد از گیت..."
    sudo -u "${RUN_USER}" git -C "${APP_DIR}" pull --ff-only \
        || warn "git pull انجام نشد؛ با نسخه فعلی کد ادامه می‌دهیم."
fi

# ---------- نصب پیش‌نیازهای سیستم ----------

info "نصب پکیج‌های سیستمی (python3, venv, pip, ffmpeg, git)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ffmpeg git

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "نسخه پایتون باید ۳.۱۰ یا بالاتر باشد."

command -v ffmpeg >/dev/null 2>&1 || die "ffmpeg نصب نشد."

# ---------- محیط مجازی و کتابخانه‌ها ----------

info "ساخت/به‌روزرسانی محیط مجازی پایتون..."
if [[ ! -d "${APP_DIR}/venv" ]]; then
    sudo -u "${RUN_USER}" python3 -m venv "${APP_DIR}/venv"
fi

sudo -u "${RUN_USER}" "${APP_DIR}/venv/bin/pip" install --upgrade pip
sudo -u "${RUN_USER}" "${APP_DIR}/venv/bin/pip" install --upgrade -r "${APP_DIR}/requirements.txt"

# ---------- فایل .env ----------

if [[ ! -f "${ENV_FILE}" ]]; then
    info "ساخت فایل .env"

    token="${BOT_TOKEN:-}"
    if [[ -z "${token}" ]]; then
        read -rsp "توکن ربات (از @BotFather): " token </dev/tty \
            || die "ورودی تعاملی در دسترس نیست. متغیر BOT_TOKEN را تنظیم کنید."
        echo
    fi
    [[ -n "${token}" ]] || die "توکن خالی است."

    cat > "${ENV_FILE}" <<EOF
BOT_TOKEN=${token}
AUDIO_BITRATE=192
MAX_TRACKS=50
EOF
    chmod 600 "${ENV_FILE}"
    chown "${RUN_USER}:${RUN_USER}" "${ENV_FILE}"
else
    info "فایل .env از قبل وجود دارد و تغییر نمی‌کند."
fi

chown -R "${RUN_USER}:${RUN_USER}" "${APP_DIR}/venv"

# ---------- سرویس systemd ----------

info "ساخت سرویس systemd..."
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Telegram Music Downloader Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python ${APP_DIR}/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${APP_NAME}" >/dev/null
systemctl restart "${APP_NAME}"

sleep 3
if systemctl is-active --quiet "${APP_NAME}"; then
    info "ربات با موفقیت اجرا شد."
else
    die "سرویس اجرا نشد. لاگ‌ها: journalctl -u ${APP_NAME} -n 50 --no-pager"
fi

# ---------- خلاصه ----------

cat <<EOF

================ نصب کامل شد ================
وضعیت:            systemctl status ${APP_NAME}
مشاهده لاگ زنده:  journalctl -u ${APP_NAME} -f
ری‌استارت:        sudo systemctl restart ${APP_NAME}
توقف:             sudo systemctl stop ${APP_NAME}
به‌روزرسانی:      git pull && sudo ./install.sh
=============================================
EOF
