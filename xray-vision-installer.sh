#!/usr/bin/env bash
# ======================================================================
# Xray Vision Installer - Menu
# Builder : racunzx
# GitHub  : https://github.com/racunzx/Xray-Vision-Installer
# Version : 2.1
# Date    : 2025-08-25
# License : MIT
# ======================================================================
set -euo pipefail

# ---------------- Colors ----------------
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info(){ echo -e "${YELLOW}INFO:${NC} $*"; }
success(){ echo -e "${GREEN}OK:${NC} $*"; }
error(){ echo -e "${RED}ERR:${NC} $*" >&2; }

# ---------------- Paths & Vars ----------------
XRAY_PATH="/usr/local/etc/xray"
NGINX_CONF_PATH="/etc/nginx/conf.d"
ACME_HOME="$HOME/.acme.sh"
ACME_SH="$ACME_HOME/acme.sh"
LOG_FILE="/var/log/xray-installer.log"
DOMAIN=""
DEPLOY_MODE=""
CERT_MODE=""
SECRET_PATH=""
UUID_LIST_FILE="$XRAY_PATH/uuid.list"

# ---------------- Preconditions ----------------
need_root(){ [ "$(id -u)" -eq 0 ] || error "Run as root (sudo)."; }

# ---------------- Core Functions ----------------
install_dependencies(){
    info "Installing dependencies..."
    apt update && apt upgrade -y
    apt install -y curl wget socat qrencode unzip lsof jq nginx || true
    systemctl stop nginx || true
}

install_acme(){
    info "Installing acme.sh..."
    [ -f "$ACME_SH" ] || curl https://get.acme.sh | sh
}

issue_cert(){
    case "$CERT_MODE" in
        standalone)
            info "Issuing TLS cert (Standalone)..."
            "$ACME_SH" --issue -d "$DOMAIN" --standalone -k ec-256 ;;
        cloudflare)
            info "Issuing TLS cert via Cloudflare..."
            [ -n "${CF_Email:-}" ] && [ -n "${CF_Key:-}" ] || error "CF_Email/CF_Key not set"
            export CF_Email CF_Key
            "$ACME_SH" --issue --dns dns_cf -d "$DOMAIN" -k ec-256 ;;
        *) error "Unknown CERT_MODE" ;;
    esac
}

install_cert_to(){
    local key_file="$1" fullchain_file="$2"
    info "Installing cert to $key_file / $fullchain_file"
    "$ACME_SH" --install-cert -d "$DOMAIN" --ecc \
        --key-file "$key_file" \
        --fullchain-file "$fullchain_file"
}

install_xray(){
    info "Installing Xray-core..."
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
    mkdir -p "$XRAY_PATH"
    [ -f "$UUID_LIST_FILE" ] || touch "$UUID_LIST_FILE"
}

config_xray_direct(){
    info "Configuring Xray Direct TLS..."
    SECRET_PATH=""
    local uuid="$(uuidgen)"
    echo "$uuid" >> "$UUID_LIST_FILE"
    cat >"$XRAY_PATH/config.json" <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [ { "id": "$uuid", "flow": "xtls-rprx-vision", "level": 0 } ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
          "certificates": [
            { "certificateFile": "$XRAY_PATH/server.crt", "keyFile": "$XRAY_PATH/server.key" }
          ]
        }
      }
    }
  ],
  "outbounds": [ { "protocol": "freedom" } ]
}
EOF
    success "Xray Direct TLS configured. UUID added: $uuid"
}

config_xray_nginx_backend(){
    info "Configuring Xray backend for Nginx..."
    SECRET_PATH="/$(uuidgen | cut -d'-' -f1)"
    local uuid="$(uuidgen)"
    echo "$uuid $SECRET_PATH" >> "$UUID_LIST_FILE"
    cat >"$XRAY_PATH/config.json" <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "listen": "127.0.0.1",
      "port": 10086,
      "protocol": "vless",
      "settings": {
        "clients": [ { "id": "$uuid", "flow": "xtls-rprx-vision", "level": 0 } ],
        "decryption": "none"
      },
      "streamSettings": { "network": "tcp" }
    }
  ],
  "outbounds": [ { "protocol": "freedom" } ]
}
EOF
    success "Xray backend configured. UUID: $uuid, Path: $SECRET_PATH"
}

config_nginx(){
    info "Configuring Nginx reverse proxy..."
    rm -f /etc/nginx/sites-enabled/default || true
    cat >"$NGINX_CONF_PATH/xray.conf" <<EOF
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate     /etc/ssl/certs/v2ray.crt;
    ssl_certificate_key /etc/ssl/private/v2ray.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / { root /var/www/html; index index.html; }

    location $SECRET_PATH {
      proxy_pass http://127.0.0.1:10086;
      proxy_http_version 1.1;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_redirect off;
    }
}
EOF
    nginx -t
}

service_hardening(){
    info "Enabling xray service auto-restart..."
    systemctl enable xray
    mkdir -p /etc/systemd/system/xray.service.d
    cat >/etc/systemd/system/xray.service.d/override.conf <<'OVR'
[Service]
Restart=always
RestartSec=5
OVR
    systemctl daemon-reload
}

open_firewall(){
    info "Opening firewall ports..."
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 80/tcp || true
        ufw allow 443/tcp || true
    else
        iptables -I INPUT -p tcp --dport 80 -j ACCEPT || true
        iptables -I INPUT -p tcp --dport 443 -j ACCEPT || true
    fi
}

show_users(){
    info "Listing all UUIDs:"
    cat "$UUID_LIST_FILE" || echo "No users yet."
}

add_user(){
    read -rp "Masukkan jumlah user baru: " n
    for ((i=0;i<n;i++)); do
        local uuid="$(uuidgen)"
        if [ "$DEPLOY_MODE" = "direct" ]; then
            echo "$uuid" >> "$UUID_LIST_FILE"
            info "Added UUID: $uuid"
        else
            local path="/$(uuidgen | cut -d'-' -f1)"
            echo "$uuid $path" >> "$UUID_LIST_FILE"
            info "Added UUID: $uuid, Path: $path"
        fi
    done
    systemctl restart xray
}

remove_user(){
    show_users
    read -rp "Masukkan UUID untuk remove: " rm_uuid
    sed -i "/$rm_uuid/d" "$UUID_LIST_FILE"
    systemctl restart xray
    info "Removed UUID: $rm_uuid"
}

renew_cert(){
    info "Renewing certificate..."
    "$ACME_SH" --renew -d "$DOMAIN" --force
    info "Certificate renewed. Restart services..."
    systemctl restart xray nginx || true
}

backup_config(){
    local backup_file="$HOME/xray_backup_$(date +%F).tar.gz"
    tar czf "$backup_file" "$XRAY_PATH" /etc/ssl/private/v2ray.key /etc/ssl/certs/v2ray.crt "$NGINX_CONF_PATH/xray.conf"
    success "Backup saved to $backup_file"
}

restore_config(){
    read -rp "Masukkan path backup file: " bf
    tar xzf "$bf" -C /
    systemctl restart xray nginx || true
    success "Restore done."
}

show_log(){
    tail -n 30 "$LOG_FILE" || echo "No log yet."
}

uninstall_flow(){
    info "Stopping services..."
    systemctl stop xray nginx || true
    info "Removing Xray..."
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ remove --purge || true
    rm -rf "$XRAY_PATH"
    rm -f "$NGINX_CONF_PATH/xray.conf" /etc/ssl/private/v2ray.key /etc/ssl/certs/v2ray.crt
    success "Uninstall completed."
}

# ---------------- Menu Flow ----------------
install_flow(){
    need_root
    read -rp "Masukkan domain anda: " DOMAIN
    [ -z "$DOMAIN" ] && error "Domain tidak boleh kosong!"

    echo "Pilih deploy mode: 1) Direct TLS 2) Nginx Proxy"
    read -rp "Pilihan: " dm
    DEPLOY_MODE=$([ "$dm" = "2" ] && echo nginx || echo direct)

    echo "Pilih certificate mode: 1) Standalone 2) Cloudflare DNS API"
    read -rp "Pilihan: " cm
    if [ "$cm" = "2" ]; then
        CERT_MODE=cloudflare
        read -rp "CF Email: " CF_Email
        read -rp "CF Global API Key: " CF_Key
        export CF_Email CF_Key
    else
        CERT_MODE=standalone
    fi

    install_dependencies
    install_acme
    issue_cert
    install_xray

    if [ "$DEPLOY_MODE" = "direct" ]; then
        install_cert_to "$XRAY_PATH/server.key" "$XRAY_PATH/server.crt"
        config_xray_direct
    else
        install_cert_to "/etc/ssl/private/v2ray.key" "/etc/ssl/certs/v2ray.crt"
        config_xray_nginx_backend
        config_nginx
    fi
    service_hardening
    open_firewall
    systemctl restart xray nginx || true
    success "Installation completed!"
}

main_menu(){
    while true; do
        clear
        # ---------------- Banner ASCII ----------------
        echo -e "${YELLOW}▒██   ██▒ ██▀███   ▄▄▄     ▓██   ██▓    ██▒   █▓ ██▓  ██████  ██▓ ▒█████   ███▄    █ "
        echo -e "▒▒ █ █ ▒░▓██ ▒ ██▒▒████▄    ▒██  ██▒   ▓██░   █▒▓██▒▒██    ▒ ▓██▒▒██▒  ██▒ ██ ▀█   █ "
        echo -e "░░  █   ░▓██ ░▄█ ▒▒██  ▀█▄   ▒██ ██░    ▓██  █▒░▒██▒░ ▓██▄   ▒██▒▒██░  ██▒▓██  ▀█ ██▒"
        echo -e " ░ █ █ ▒ ▒██▀▀█▄  ░██▄▄▄▄██  ░ ▐██▓░     ▒██ █░░░██░  ▒   ██▒░██░▒██   ██░▓██▒  ▐▌██▒"
        echo -e "▒██▒ ▒██▒░██▓ ▒██▒ ▓█   ▓██▒ ░ ██▒▓░      ▒▀█░  ░██░▒██████▒▒░██░░ ████▓▒░▒██░   ▓██░"
        echo -e "▒▒ ░ ░▓ ░░ ▒▓ ░▒▓░ ▒▒   ▓▒█░  ██▒▒▒       ░ ▐░  ░▓  ▒ ▒▓▒ ▒ ░░▓  ░ ▒░▒░▒░ ░ ▒░   ▒ ▒ "
        echo -e "░░   ░▒ ░  ░▒ ░ ▒░  ▒   ▒▒ ░▓██ ░▒░       ░ ░░   ▒ ░░ ░▒  ░ ░ ▒ ░  ░ ▒ ▒░ ░ ░░   ░ ▒░"
        echo -e " ░    ░    ░░   ░   ░   ▒   ▒ ▒ ░░          ░░   ▒ ░░  ░  ░   ▒ ░░ ░ ░ ▒     ░   ░ ░ "
        echo -e " ░    ░     ░           ░  ░░ ░              ░   ░        ░   ░      ░ ░           ░ "
        echo -e "                            ░ ░             ░${NC}"
        # ---------------- Menu ----------------
        echo "=============================================="
        echo " Xray Vision Installer - racunzx "
        echo "=============================================="
        echo "1) Install Xray Server"
        echo "2) Add User"
        echo "3) List Users"
        echo "4) Remove User"
        echo "5) Renew Certificate"
        echo "6) Backup Config"
        echo "7) Restore Config"
        echo "8) Show Log"
        echo "9) Uninstall"
        echo "0) Exit"
        read -rp "Pilihan: " opt
        case "$opt" in
            1) install_flow ;;
            2) add_user ;;
            3) show_users ;;
            4) remove_user ;;
            5) renew_cert ;;
            6) backup_config ;;
            7) restore_config ;;
            8) show_log ;;
            9) uninstall_flow ;;
            0) exit 0 ;;
            *) echo "Pilihan salah!" ;;
        esac
    done
}

# ---------------- Entry Point ----------------
main_menu
