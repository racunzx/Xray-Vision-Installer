#!/usr/bin/env bash
# ======================================================================
# Xray Universal Installer (Direct TLS / Nginx Proxy) + (Standalone / CF)
# Builder : racunzx
# GitHub  : https://github.com/racunzx/Xray-Vision-Installer
# Version : 2.0
# Date    : 2025-08-25
# License : MIT
# ======================================================================
set -euo pipefail

# ---------------- Colors ----------------
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info(){ echo -e "${YELLOW}INFO:${NC} $*"; }
success(){ echo -e "${GREEN}OK:${NC} $*"; }
error(){ echo -e "${RED}ERR:${NC} $*" >&2; exit 1; }

# ---------------- Paths & Vars ----------------
XRAY_PATH="/usr/local/etc/xray"
NGINX_CONF_PATH="/etc/nginx/conf.d"
ACME_HOME="$HOME/.acme.sh"
ACME_SH="$ACME_HOME/acme.sh"
UUID="$(cat /proc/sys/kernel/random/uuid)"
SECRET_PATH="/$(echo "$UUID" | cut -d'-' -f1)"   # e.g. /3f3f3a2e
CERT_MODE=""       # standalone|cloudflare
DEPLOY_MODE=""     # direct|nginx
DOMAIN=""

# ---------------- Preconditions ----------------
need_root(){ [ "$(id -u)" -eq 0 ] || error "Run as root (sudo)."; }

install_dependencies(){
  info "Installing dependencies..."
  apt update && apt upgrade -y
  apt install -y curl wget socat qrencode unzip lsof jq
  if [ "$DEPLOY_MODE" = "nginx" ]; then
    apt install -y nginx
    systemctl stop nginx || true
  fi
}

install_acme(){
  info "Installing acme.sh..."
  if [ ! -f "$ACME_SH" ]; then
    curl https://get.acme.sh | sh
  fi
}

issue_cert(){
  case "$CERT_MODE" in
    standalone)
      info "Issuing TLS cert (Standalone, uses port 80)..."
      "$ACME_SH" --issue -d "$DOMAIN" --standalone -k ec-256 ;;
    cloudflare)
      info "Issuing TLS cert via Cloudflare DNS API..."
      [ -n "${CF_Email:-}" ] && [ -n "${CF_Key:-}" ] || error "CF_Email/CF_Key env not set"
      export CF_Email CF_Key
      "$ACME_SH" --issue --dns dns_cf -d "$DOMAIN" -k ec-256 ;;
    *) error "Unknown CERT_MODE: $CERT_MODE" ;;
  esac
}

install_cert_to(){
  local key_file="$1" fullchain_file="$2"
  info "Installing cert to: $key_file / $fullchain_file"
  mkdir -p "$(dirname "$key_file")" "$(dirname "$fullchain_file")"
  "$ACME_SH" --install-cert -d "$DOMAIN" --ecc \
    --key-file       "$key_file" \
    --fullchain-file "$fullchain_file"
  [ -f "$fullchain_file" ] || error "Cert install failed"
}

install_xray(){
  info "Installing Xray-core..."
  bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
  mkdir -p "$XRAY_PATH"
}

config_xray_direct(){
  info "Configuring Xray (Direct TLS on 443)..."
  cat >"$XRAY_PATH/config.json" <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [ { "id": "$UUID", "flow": "xtls-rprx-vision", "level": 0 } ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
          "certificates": [ { "certificateFile": "$XRAY_PATH/server.crt", "keyFile": "$XRAY_PATH/server.key" } ]
        }
      }
    }
  ],
  "outbounds": [ { "protocol": "freedom" } ]
}
EOF
}

config_xray_nginx_backend(){
  info "Configuring Xray (backend on 127.0.0.1:10086)..."
  cat >"$XRAY_PATH/config.json" <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "listen": "127.0.0.1",
      "port": 10086,
      "protocol": "vless",
      "settings": {
        "clients": [ { "id": "$UUID", "flow": "xtls-rprx-vision", "level": 0 } ],
        "decryption": "none"
      },
      "streamSettings": { "network": "tcp" }
    }
  ],
  "outbounds": [ { "protocol": "freedom" } ]
}
EOF
}

config_nginx(){
  info "Configuring Nginx reverse proxy (path: $SECRET_PATH)..."
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
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
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
  if command -v ufw >/dev/null 2>&1; then
    info "Configuring UFW..."
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
  else
    info "Opening ports with iptables..."
    iptables -I INPUT -p tcp --dport 80 -j ACCEPT || true
    iptables -I INPUT -p tcp --dport 443 -j ACCEPT || true
  fi
}

show_result_direct(){
  local LINK="vless://${UUID}@${DOMAIN}:443?encryption=none&security=tls&type=tcp&flow=xtls-rprx-vision&sni=${DOMAIN}#${DOMAIN}_VLESS_Vision"
  echo "===================================================="
  success "Installation Completed (Direct TLS)"
  info "Domain : $DOMAIN"
  info "UUID   : $UUID"
  echo ""; info "VLESS Link:"; echo -e "${GREEN}$LINK${NC}"
  echo ""; info "QR Code:"; qrencode -t ANSIUTF8 "$LINK" || true
  echo "===================================================="
}

show_result_nginx(){
  local LINK="vless://${UUID}@${DOMAIN}:443?encryption=none&security=tls&type=tcp&flow=xtls-rprx-vision&sni=${DOMAIN}&path=${SECRET_PATH}#${DOMAIN}_VLESS_Vision"
  echo "===================================================="
  success "Installation Completed (Nginx Proxy)"
  info "Domain : $DOMAIN"
  info "UUID   : $UUID"
  info "Path   : $SECRET_PATH"
  echo ""; info "VLESS Link:"; echo -e "${GREEN}$LINK${NC}"
  echo ""; info "QR Code:"; qrencode -t ANSIUTF8 "$LINK" || true
  echo "===================================================="
}

install_flow(){
  need_root
  clear
  echo "=============================================="
  echo " Xray Universal Installer (by racunzx) "
  echo "=============================================="
  read -rp "Masukkan domain anda (cth mydomain.com): " DOMAIN
  [ -z "$DOMAIN" ] && error "Domain tidak boleh kosong"

  echo -e "\nPilih deploy mode:"
  echo "  1) Direct TLS (Xray on :443)"
  echo "  2) Nginx Proxy (camouflage + secret path)"
  read -rp "Pilihan (1/2): " dm
  DEPLOY_MODE=$([ "$dm" = "2" ] && echo nginx || echo direct)

  echo -e "\nPilih certificate mode:"
  echo "  1) Standalone (guna port 80)"
  echo "  2) Cloudflare DNS API"
  read -rp "Pilihan (1/2): " cm
  if [ "$cm" = "2" ]; then
    CERT_MODE=cloudflare
    read -rp "Cloudflare Email: " CF_Email
    read -rp "Cloudflare Global API Key: " CF_Key
    export CF_Email CF_Key
  else
    CERT_MODE=standalone
  fi

  install_dependencies
  install_acme
  issue_cert

  install_xray

  if [ "$DEPLOY_MODE" = "direct" ]; then
    # Put certs inside xray dir
    install_cert_to "$XRAY_PATH/server.key" "$XRAY_PATH/server.crt"
    config_xray_direct
    service_hardening
    open_firewall
    systemctl restart xray
    show_result_direct
  else
    # Nginx mode: put certs under /etc/ssl for nginx
    install_cert_to "/etc/ssl/private/v2ray.key" "/etc/ssl/certs/v2ray.crt"
    config_xray_nginx_backend
    config_nginx
    service_hardening
    open_firewall
    info "Restarting services..."
    systemctl restart xray
    systemctl restart nginx
    show_result_nginx
  fi
}

uninstall_flow(){
  need_root
  info "Stopping services..."
  systemctl stop xray || true
  systemctl stop nginx || true

  info "Removing Xray..."
  bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ remove --purge || true
  rm -rf "$XRAY_PATH"

  info "Removing Nginx config (if any)..."
  rm -f "$NGINX_CONF_PATH/xray.conf" || true
  if command -v nginx >/dev/null 2>&1; then
    systemctl restart nginx || true
  fi

  info "Removing installed cert files..."
  rm -f /etc/ssl/private/v2ray.key /etc/ssl/certs/v2ray.crt || true
  rm -f "$XRAY_PATH/server.key" "$XRAY_PATH/server.crt" || true

  success "Uninstall completed."
}

usage(){ echo "Usage: $0 {install|uninstall}"; }

case "${1:-}" in
  install) install_flow ;;
  uninstall) uninstall_flow ;;
  *) usage; exit 1 ;;
esac
