#!/bin/bash
# ========================================
# Telegram Xray Manager Bot Installer
# ========================================

set -e

echo "======================================="
echo "   🚀 Xray Manager Telegram Bot Setup  "
echo "======================================="

# 1. Tanya token & admin id
read -p "Masukkan Telegram Bot Token: " BOT_TOKEN
read -p "Masukkan Telegram Admin ID: " ADMIN_ID

# 2. Update & pasang dependency
echo "[*] Update & install dependencies..."
apt-get update -y
apt-get install -y python3 python3-pip git curl jq qrencode

# 3. Direktori bot
BOT_DIR="/opt/xraybot"
if [ ! -d "$BOT_DIR" ]; then
    mkdir -p $BOT_DIR
fi

# 4. Salin skrip bot (anggap bot.py sudah ada di folder semasa)
echo "[*] Salin skrip bot ke $BOT_DIR..."
cp -r ./bot.py $BOT_DIR/

# 5. Buat venv & pasang python deps
cd $BOT_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install python-telegram-bot==20.7 qrcode[pil]

# 6. Simpan env ke .env
cat > $BOT_DIR/.env <<EOF
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
ADMIN_USER_ID=${ADMIN_ID}
EOF

# 7. Buat systemd service
echo "[*] Setup systemd service..."
cat > /etc/systemd/system/xraybot.service <<EOF
[Unit]
Description=Telegram Bot for Xray Manager
After=network.target

[Service]
User=root
WorkingDirectory=${BOT_DIR}
EnvironmentFile=${BOT_DIR}/.env
ExecStart=${BOT_DIR}/venv/bin/python ${BOT_DIR}/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 8. Reload & start service
systemctl daemon-reload
systemctl enable xraybot
systemctl restart xraybot

echo "======================================="
echo "✅ Bot sudah dipasang & berjalan!"
echo "   Log: journalctl -u xraybot -f"
echo "======================================="
