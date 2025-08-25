#!/usr/bin/env bash
# ==============================================
# Telegram Xray Manager Bot Installer BY racunzx
# ==============================================
set -euo pipefail

echo "=========================================="
echo "  Xray Telegram Bot Installer BY racunzx"
echo "=========================================="

BOT_DIR="/opt/xraybot"
ENV_FILE="/etc/xray-bot.env"
SERVICE_FILE="/etc/systemd/system/xray-bot.service"
BOT_PY="xray_bot.py"
VENV_DIR="$BOT_DIR/venv"

if [[ $(id -u) -ne 0 ]]; then
    echo "Run installer as root (sudo)"
    exit 1
fi

read -rp "Masukkan TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
read -rp "Masukkan ADMIN_USER_ID: " ADMIN_USER_ID

apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl jq qrencode

mkdir -p "$BOT_DIR"
if [[ ! -f "./$BOT_PY" ]]; then
    echo "❌ Fail $BOT_PY tidak ditemui di direktori semasa"
    exit 1
fi

cp "./$BOT_PY" "$BOT_DIR/"
chmod 750 "$BOT_DIR/$BOT_PY"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install python-telegram-bot==20.7 qrcode

cat > "$ENV_FILE" <<EOF
TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
ADMIN_USER_ID="$ADMIN_USER_ID"
EOF
chmod 600 "$ENV_FILE"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Xray Telegram Manager Bot
After=network-online.target

[Service]
Type=simple
User=root
EnvironmentFile=$ENV_FILE
WorkingDirectory=$BOT_DIR
ExecStart=$VENV_DIR/bin/python $BOT_DIR/$BOT_PY
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable xray-bot.service
systemctl restart xray-bot.service

sleep 1
systemctl is-active --quiet xray-bot.service && \
    echo "✅ xray-bot.service active" || echo "⚠️ xray-bot.service not active"

echo "Installer selesai. Log bot: /var/log/xray_bot.log"
