#!/usr/bin/env bash
# ======================================================================
# Xray Vision Installer 6-in-1 Final
# Builder : racunzx
# Version : 3.1
# Date    : 2025-08-25
# ======================================================================
set -euo pipefail

# ---------------- Colors ----------------
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
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
        none) info "Skipping certificate issuance..." ;;
        *) error "Unknown CERT_MODE" ;;
    esac
}

install_xray(){
    info "Installing Xray-core..."
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
    mkdir -p "$XRAY_PATH"
    [ -f "$UUID_LIST_FILE" ] || touch "$UUID_LIST_FILE"
}

# ---------------- Xray Config ----------------
generate_uuid(){ uuidgen; }

config_xray_direct(){
    SECRET_PATH=""
    local uuid="$(generate_uuid)"
    echo "$uuid" >> "$UUID_LIST_FILE"
    cat >"$XRAY_PATH/config.json" <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [ { "port": 443, "protocol": "vless", "settings": { "clients": [ { "id": "$uuid", "flow": "xtls-rprx-vision", "level": 0 } ], "decryption": "none" }, "streamSettings": { "network": "tcp", "security": "tls", "tlsSettings": { "certificates": [ { "certificateFile": "$XRAY_PATH/server.crt", "keyFile": "$XRAY_PATH/server.key" } ] } } } ],
  "outbounds": [ { "protocol": "freedom" } ]
}
EOF
    success "Xray Direct TLS configured. UUID: $uuid"
    echo -e "${CYAN}VLESS URI:${NC} vless://${uuid}@${DOMAIN}:443?security=tls&flow=xtls-rprx-vision&type=tcp#Xray-Direct"
    echo -n "QR Code: "; qrencode -t ansiutf8 "vless://${uuid}@${DOMAIN}:443?security=tls&flow=xtls-rprx-vision&type=tcp#Xray-Direct"
}

config_xray_nginx_backend(){
    SECRET_PATH="/$(generate_uuid | cut -d'-' -f1)"
    local uuid="$(generate_uuid)"
    echo "$uuid $SECRET_PATH" >> "$UUID_LIST_FILE"
    cat >"$XRAY_PATH/config.json" <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [ { "listen": "127.0.0.1", "port": 10086, "protocol": "vless", "settings": { "clients": [ { "id": "$uuid", "flow": "xtls-rprx-vision", "level": 0 } ], "decryption": "none" }, "streamSettings": { "network": "tcp" } } ],
  "outbounds": [ { "protocol": "freedom" } ]
}
EOF
    success "Xray backend configured. UUID: $uuid, Path: $SECRET_PATH"
    echo -e "${CYAN}VLESS URI:${NC} vless://${uuid}@${DOMAIN}:443?security=tls&flow=xtls-rprx-vision&type=tcp&sni=${DOMAIN}#Xray-Nginx"
    echo -n "QR Code: "; qrencode -t ansiutf8 "vless://${uuid}@${DOMAIN}:443?security=tls&flow=xtls-rprx-vision&type=tcp&sni=${DOMAIN}#Xray-Nginx"
}

config_nginx(){
    info "Configuring Nginx reverse proxy..."
    cat >"$NGINX_CONF_PATH/xray.conf" <<EOF
server {
    listen 443 ssl http2;
    server_name $DOMAIN;
    ssl_certificate     /etc/ssl/certs/v2ray.crt;
    ssl_certificate_key /etc/ssl/private/v2ray.key;
    location $SECRET_PATH {
      proxy_pass http://127.0.0.1:10086;
      proxy_http_version 1.1;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF
    nginx -t
}

service_hardening(){
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
    iptables -I INPUT -p tcp --dport 80 -j ACCEPT || true
    iptables -I INPUT -p tcp --dport 443 -j ACCEPT || true
}

# ---------------- User Management ----------------
add_user(){ read -rp "Jumlah user baru: " n; for ((i=0;i<n;i++)); do uuid="$(generate_uuid)"; echo "$uuid" >> "$UUID_LIST_FILE"; done; systemctl restart xray; }
show_users(){ cat "$UUID_LIST_FILE" || echo "No users yet."; }
remove_user(){ show_users; read -rp "UUID untuk remove: " rm_uuid; sed -i "/$rm_uuid/d" "$UUID_LIST_FILE"; systemctl restart xray; }

renew_cert(){ "$ACME_SH" --renew -d "$DOMAIN" --force; systemctl restart xray nginx || true; }
backup_config(){ tar czf "$HOME/xray_backup_$(date +%F).tar.gz" "$XRAY_PATH" /etc/ssl/private/v2ray.key /etc/ssl/certs/v2ray.crt "$NGINX_CONF_PATH/xray.conf"; }
restore_config(){ read -rp "Path backup: " bf; tar xzf "$bf" -C /; systemctl restart xray nginx || true; }

uninstall_flow(){
    systemctl stop xray nginx || true
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ remove --purge || true
    rm -rf "$XRAY_PATH" "$NGINX_CONF_PATH/xray.conf" /etc/ssl/private/v2ray.key /etc/ssl/certs/v2ray.crt
}

# ---------------- Menu ----------------
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
        echo "8) Uninstall"
        echo "0) Exit"
        read -rp "Pilihan: " opt
        case "$opt" in
            1)
                need_root
                read -rp "Domain anda: " DOMAIN
                echo "Versi:"
                echo "1) Direct + Standalone"
                echo "2) Direct + Cloudflare"
                echo "3) Nginx + Standalone"
                echo "4) Nginx + Cloudflare"
                echo "5) Reality Direct"
                echo "6) Reality Nginx"
                read -rp "Pilihan: " v
                case "$v" in
                    1) DEPLOY_MODE="direct"; CERT_MODE="standalone" ;;
                    2) DEPLOY_MODE="direct"; CERT_MODE="cloudflare" ;;
                    3) DEPLOY_MODE="nginx"; CERT_MODE="standalone" ;;
                    4) DEPLOY_MODE="nginx"; CERT_MODE="cloudflare" ;;
                    5) DEPLOY_MODE="reality"; CERT_MODE="none" ;;
                    6) DEPLOY_MODE="nginx-reality"; CERT_MODE="none" ;;
                    *) error "Pilihan salah!"; continue ;;
                esac
                install_dependencies
                [ "$CERT_MODE" != "none" ] && install_acme && issue_cert
                install_xray
                if [[ "$DEPLOY_MODE" =~ ^direct$ ]]; then
                    install_cert_to "$XRAY_PATH/server.key" "$XRAY_PATH/server.crt"
                    config_xray_direct
                elif [[ "$DEPLOY_MODE" =~ ^nginx$ ]]; then
                    install_cert_to "/etc/ssl/private/v2ray.key" "/etc/ssl/certs/v2ray.crt"
                    config_xray_nginx_backend
                    config_nginx
                else
                    info "Reality mode: skipping TLS"
                fi
                service_hardening
                open_firewall
                systemctl restart xray nginx || true
                success "Installation completed!"
                ;;
            2) add_user ;;
            3) show_users ;;
            4) remove_user ;;
            5) renew_cert ;;
            6) backup_config ;;
            7) restore_config ;;
            8) uninstall_flow ;;
            0) exit 0 ;;
            *) echo "Pilihan salah!" ;;
        esac
    done
}

main_menu
