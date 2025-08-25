#!/usr/bin/env bash
# ==============================================
# Telegram Xray Manager Bot Installer BY racunzx
# ==============================================
set -euo pipefail

# Installer for Xray Telegram Bot
BOT_DIR="/opt/xraybot"
ENV_FILE="/etc/xray-bot.env"
SERVICE_FILE="/etc/systemd/system/xray-bot.service"
BOT_PY="bot.py"  # pastikan bot.py ada di current dir
VENV_DIR="$BOT_DIR/venv"

echo "=========================================="
echo "  Xray Telegram Bot Installer BY racunzx"
echo "=========================================="

if [[ $(id -u) -ne 0 ]]; then
  echo "Run installer as root (sudo). Exiting."
  exit 1
fi

# Prompt token & admin id
read -rp "Masukkan TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
read -rp "Masukkan ADMIN_USER_ID: " ADMIN_USER_ID

if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$ADMIN_USER_ID" ]]; then
  echo "TOKEN atau ADMIN ID kosong. Exiting."
  exit 1
fi

# Install system deps
echo "[1/6] Install system packages..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl jq

# Prepare bot directory
echo "[2/6] Preparing bot directory: $BOT_DIR"
mkdir -p "$BOT_DIR"
chown root:root "$BOT_DIR"
chmod 755 "$BOT_DIR"

# Copy bot.py
if [[ ! -f "./$BOT_PY" ]]; then
  echo "File $BOT_PY tidak ditemui di current dir. Sila letak bot.py di sini."
  exit 1
fi
cp "./$BOT_PY" "$BOT_DIR/$BOT_PY"
chmod 750 "$BOT_DIR/$BOT_PY"
chown root:root "$BOT_DIR/$BOT_PY"

# Create virtualenv & install python deps
echo "[3/6] Creating virtualenv & installing Python packages..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install python-telegram-bot==20.7

# Write env file
echo "[4/6] Writing environment file $ENV_FILE ..."
cat > "$ENV_FILE" <<EOF
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
ADMIN_USER_ID="${ADMIN_USER_ID}"
EOF
chmod 600 "$ENV_FILE"
chown root:root "$ENV_FILE"

# Create systemd service
echo "[5/6] Creating systemd service $SERVICE_FILE ..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Xray Telegram Bot
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

# Enable & start service
echo "[6/6] Reloading systemd, enabling & starting xray-bot.service..."
systemctl daemon-reload
systemctl enable xray-bot.service
systemctl restart xray-bot.service

sleep 1
systemctl is-active --quiet xray-bot.service && \
  echo "✅ xray-bot.service active" || echo "⚠️ xray-bot.service not active - check journalctl -u xray-bot.service"

echo "Installer selesai."
echo "Lihat log bot: journalctl -u xray-bot.service -f"
