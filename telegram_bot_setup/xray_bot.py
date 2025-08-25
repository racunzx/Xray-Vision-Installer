#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot: Xray/VLESS Manager (Inline Menu)
Author  : racunzx
Repo    : https://github.com/racunzx/Xray-Vision-Installer
Version : 1.0 Final
"""

import os
import json
import logging
import subprocess
import io
from datetime import datetime, timedelta
from uuid import uuid4
import qrcode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =====================
# Logging
# =====================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("/var/log/xray_bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# =====================
# Config / Env
# =====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_USER_ID", "0"))
DATA_FILE = "/etc/xray/users.json"
CONFIG_FILE = "/etc/xray/config.json"
DOMAIN_FILE = "/etc/xray/domain.json"

# =====================
# Pastikan file wujud
# =====================
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)
if not os.path.exists(DOMAIN_FILE):
    with open(DOMAIN_FILE, "w") as f:
        json.dump({"domain": "", "mode": "direct"}, f)

# =====================
# Helper Functions
# =====================
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_domain():
    with open(DOMAIN_FILE) as f:
        return json.load(f)

def save_domain(domain):
    with open(DOMAIN_FILE, "w") as f:
        json.dump(domain, f, indent=2)

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def gen_uuid():
    return str(uuid4())

def gen_vless_link(user_id, uuid, domain, mode, exp):
    if mode == "nginx":
        return f"vless://{uuid}@{domain}:443?path=/{user_id}&security=tls&encryption=none&type=ws#{user_id}"
    else:
        return f"vless://{uuid}@{domain}:443?security=tls&encryption=none&type=tcp#{user_id}"

def gen_qr(link):
    img = qrcode.make(link)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def restart_xray():
    subprocess.run(["systemctl", "restart", "xray"], check=False)

def inject_to_config(user_id, uuid, exp):
    cfg = load_config()
    new_client = {"id": uuid, "email": user_id, "expiryTime": exp}
    if "inbounds" in cfg and len(cfg["inbounds"]) > 0:
        if "settings" in cfg["inbounds"][0] and "clients" in cfg["inbounds"][0]["settings"]:
            cfg["inbounds"][0]["settings"]["clients"].append(new_client)
    save_config(cfg)
    restart_xray()

# =====================
# Menu Inline
# =====================
def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Status Server", callback_data="status"),
         InlineKeyboardButton("👥 Senarai User", callback_data="list_users")],
        [InlineKeyboardButton("➕ Tambah User", callback_data="add_user"),
         InlineKeyboardButton("❌ Buang User", callback_data="del_user")],
        [InlineKeyboardButton("🔑 Renew User", callback_data="renew_user"),
         InlineKeyboardButton("📈 Trafik User", callback_data="trafik_user")],
        [InlineKeyboardButton("🔄 Restart Service", callback_data="restart"),
         InlineKeyboardButton("🧾 Tunjuk Log", callback_data="logs")],
        [InlineKeyboardButton("🔐 Renew Sijil", callback_data="renew_cert"),
         InlineKeyboardButton("⚙️ Config / Set", callback_data="config")],
        [InlineKeyboardButton("🧹 Cleanup Expired", callback_data="cleanup")],
        [InlineKeyboardButton("↩️ Kembali ke Menu Utama", callback_data="home")]
    ]
    return InlineKeyboardMarkup(keyboard)

# =====================
# Handlers
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("Selamat datang, Admin ✅", reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    action = query.data
    users = load_users()
    domain = load_domain()["domain"]
    mode = load_domain()["mode"]

    if action == "status":
        uptime = subprocess.getoutput("uptime -p")
        await query.edit_message_text(f"📊 Status Server:\n{uptime}", reply_markup=main_menu())

    elif action == "list_users":
        if not users:
            await query.edit_message_text("👥 Tiada user.", reply_markup=main_menu())
            return
        msg = "👥 Senarai User:\n"
        for u, d in users.items():
            msg += f"- {u} | Exp: {d['expired']}\n"
        await query.edit_message_text(msg, reply_markup=main_menu())

    elif action == "add_user":
        # default 30 hari
        user_id = f"user{len(users)+1}"
        uid = gen_uuid()
        exp = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        users[user_id] = {"uuid": uid, "expired": exp}
        save_users(users)
        inject_to_config(user_id, uid, exp)

        vless_link = gen_vless_link(user_id, uid, domain, mode, exp)
        qr = gen_qr(vless_link)

        await query.message.reply_text(
            f"✅ User ditambah\nUser ID: {user_id}\nExp: {exp}\nVLESS Link:\n{vless_link}"
        )
        await query.message.reply_photo(photo=InputFile(qr, filename="qr.png"))
        await query.edit_message_text("↩️ Kembali ke Menu Utama", reply_markup=main_menu())

    elif action == "del_user":
        if not users:
            await query.edit_message_text("❌ Tiada user untuk dibuang.", reply_markup=main_menu())
            return
        user_id, _ = users.popitem()
        save_users(users)
        cfg = load_config()
        if "inbounds" in cfg and len(cfg["inbounds"])>0:
            clients = cfg["inbounds"][0]["settings"]["clients"]
            cfg["inbounds"][0]["settings"]["clients"] = [c for c in clients if c["email"] != user_id]
            save_config(cfg)
            restart_xray()
        await query.edit_message_text(f"❌ User {user_id} dibuang.", reply_markup=main_menu())

    elif action == "renew_user":
        if not users:
            await query.edit_message_text("❌ Tiada user untuk renew.", reply_markup=main_menu())
            return
        user_id, data = list(users.items())[-1]
        exp = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        users[user_id]["expired"] = exp
        save_users(users)
        cfg = load_config()
        for c in cfg["inbounds"][0]["settings"]["clients"]:
            if c["email"] == user_id:
                c["expiryTime"] = exp
        save_config(cfg)
        restart_xray()
        await query.edit_message_text(f"🔑 User {user_id} renewed hingga {exp}.", reply_markup=main_menu())

    elif action == "trafik_user":
        output = subprocess.getoutput("xray api statsquery --server=127.0.0.1:10085")
        await query.edit_message_text(f"📈 Trafik User:\n{output}", reply_markup=main_menu())

    elif action == "restart":
        restart_xray()
        await query.edit_message_text("🔄 Xray restarted.", reply_markup=main_menu())

    elif action == "logs":
        logs = subprocess.getoutput("journalctl -u xray --no-pager -n 20")
        await query.edit_message_text(f"🧾 Log Terbaru:\n{logs}", reply_markup=main_menu())

    elif action == "renew_cert":
        out = subprocess.getoutput("certbot renew --quiet")
        await query.edit_message_text(f"🔐 Cert renewed:\n{out}", reply_markup=main_menu())

    elif action == "config":
        await query.edit_message_text("⚙️ Config menu (dummy sekarang).", reply_markup=main_menu())

    elif action == "cleanup":
        now = datetime.now()
        before = len(users)
        users = {u:d for u,d in users.items() if datetime.fromisoformat(d["expired"]) > now}
        save_users(users)
        cfg = load_config()
        clients = cfg["inbounds"][0]["settings"]["clients"]
        cfg["inbounds"][0]["settings"]["clients"] = [c for c in clients if datetime.fromisoformat(c["expiryTime"]) > now]
        save_config(cfg)
        restart_xray()
        after = len(users)
        await query.edit_message_text(f"🧹 Cleanup: {before-after} user expired dibuang.", reply_markup=main_menu())

    elif action == "home":
        await query.edit_message_text("↩️ Kembali ke menu utama.", reply_markup=main_menu())

# =====================
# Main
# =====================
def main():
    if not BOT_TOKEN or not ADMIN_ID:
        logger.error("BOT_TOKEN / ADMIN_ID tidak ditemui di env.")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
