#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot: Xray/VLESS Manager (Inline Menu)
Author  : racunzx
Repo    : https://github.com/racunzx/Xray-Vision-Installer
Version : 1.0 (bot standalone)
"""

import os
import json
import subprocess
import uuid
import qrcode
import io
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ============ Config Awal ============
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_USER_ID", "0"))
DATA_FILE = "/etc/xray/users.json"
CONFIG_FILE = "/etc/xray/config.json"
DOMAIN_FILE = "/etc/xray/domain.json"

# Pastikan fail wujud
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(DOMAIN_FILE):
    with open(DOMAIN_FILE, "w") as f:
        json.dump({"domain": "", "mode": "direct"}, f)


# ============ Utiliti ============
def load_users():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_domain():
    with open(DOMAIN_FILE) as f:
        return json.load(f)

def save_domain(data):
    with open(DOMAIN_FILE, "w") as f:
        json.dump(data, f, indent=2)

def gen_uuid():
    return str(uuid.uuid4())

def gen_vless_link(user_id, uuid, domain, mode, exp):
    if mode == "nginx":
        return f"vless://{uuid}@{domain}:443?path=/{user_id}&security=tls&encryption=none&type=ws#xray-{user_id}"
    else:
        return f"vless://{uuid}@{domain}:443?security=tls&encryption=none&type=tcp#xray-{user_id}"

def gen_qr(link):
    img = qrcode.make(link)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio


# ============ Menu Utama ============
def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Status Server", callback_data="status")],
        [InlineKeyboardButton("👥 Senarai User", callback_data="list_users")],
        [
            InlineKeyboardButton("➕ Tambah User", callback_data="add_user"),
            InlineKeyboardButton("❌ Padam User", callback_data="del_user")
        ],
        [
            InlineKeyboardButton("🔑 Renew User", callback_data="renew_user"),
            InlineKeyboardButton("📈 Trafik User", callback_data="trafik")
        ],
        [
            InlineKeyboardButton("🔄 Restart Service", callback_data="restart"),
            InlineKeyboardButton("⚙️ Info Config", callback_data="info")
        ],
        [InlineKeyboardButton("📜 Log Xray", callback_data="logs")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ Handler ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🤖 Xray Manager Bot\nPilih menu:", reply_markup=main_menu())


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    data = query.data

    # Status Server
    if data == "status":
        xray_status = subprocess.getoutput("systemctl is-active xray")
        nginx_status = subprocess.getoutput("systemctl is-active nginx")
        msg = f"📊 Status Server:\n- Xray: {xray_status}\n- Nginx: {nginx_status}"
        await query.edit_message_text(msg, reply_markup=main_menu())

    # Senarai User
    elif data == "list_users":
        users = load_users()
        if not users:
            await query.edit_message_text("👥 Tiada user.", reply_markup=main_menu())
            return
        msg = "👥 Senarai User:\n"
        for u, d in users.items():
            msg += f"- {u} | Exp: {d['expired']}\n"
        await query.edit_message_text(msg, reply_markup=main_menu())

    # Tambah User
    elif data == "add_user":
        user_id = f"user{len(load_users())+1}"
        uid = gen_uuid()
        domain = load_domain()["domain"]
        mode = load_domain()["mode"]
        exp = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        users = load_users()
        users[user_id] = {"uuid": uid, "expired": exp}
        save_users(users)

        link = gen_vless_link(user_id, uid, domain, mode, exp)
        qr = gen_qr(link)

        await query.message.reply_text(f"✅ User {user_id} ditambah\nExp: {exp}\n{link}")
        await query.message.reply_photo(photo=InputFile(qr, filename="qr.png"))
        await query.edit_message_text("Kembali ke menu:", reply_markup=main_menu())

    # Buang User
    elif data == "del_user":
        users = load_users()
        if not users:
            await query.edit_message_text("❌ Tiada user.", reply_markup=main_menu())
            return
        keyboard = [[InlineKeyboardButton(u, callback_data=f"del_{u}")] for u in users.keys()]
        keyboard.append([InlineKeyboardButton("↩️ Kembali", callback_data="back")])
        await query.edit_message_text("Pilih user untuk dipadam:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_"):
        user = data.split("_", 1)[1]
        users = load_users()
        if user in users:
            del users[user]
            save_users(users)
            await query.edit_message_text(f"✅ User {user} dipadam.", reply_markup=main_menu())

    # Renew User
    elif data == "renew_user":
        users = load_users()
        if not users:
            await query.edit_message_text("❌ Tiada user.", reply_markup=main_menu())
            return
        keyboard = [[InlineKeyboardButton(u, callback_data=f"renew_{u}")] for u in users.keys()]
        keyboard.append([InlineKeyboardButton("↩️ Kembali", callback_data="back")])
        await query.edit_message_text("Pilih user untuk renew:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("renew_"):
        user = data.split("_", 1)[1]
        users = load_users()
        if user in users:
            exp = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            users[user]["expired"] = exp
            save_users(users)
            await query.edit_message_text(f"✅ User {user} renewed hingga {exp}.", reply_markup=main_menu())

    # Restart Service
    elif data == "restart":
        subprocess.run("systemctl restart xray", shell=True)
        subprocess.run("systemctl restart nginx", shell=True)
        await query.edit_message_text("🔄 Service Xray & Nginx di-restart.", reply_markup=main_menu())

    # Log
    elif data == "logs":
        logs = subprocess.getoutput("journalctl -u xray --no-pager -n 20")
        await query.edit_message_text(f"📜 Log Xray (20 baris):\n{logs[-3500:]}", reply_markup=main_menu())

    # Info Config
    elif data == "info":
        d = load_domain()
        msg = f"⚙️ Config:\n- Domain: {d['domain']}\n- Mode: {d['mode']}"
        await query.edit_message_text(msg, reply_markup=main_menu())

    # Back
    elif data == "back":
        await query.edit_message_text("↩️ Menu utama:", reply_markup=main_menu())


# ============ Command Handler ============
async def setdomain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setdomain <domain>")
        return
    d = load_domain()
    d["domain"] = context.args[0]
    save_domain(d)
    await update.message.reply_text(f"✅ Domain set ke {context.args[0]}")

async def setmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 1 or context.args[0] not in ["direct", "nginx"]:
        await update.message.reply_text("Usage: /setmode <direct|nginx>")
        return
    d = load_domain()
    d["mode"] = context.args[0]
    save_domain(d)
    await update.message.reply_text(f"✅ Mode set ke {context.args[0]}")


# ============ Main ============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setdomain", setdomain))
    app.add_handler(CommandHandler("setmode", setmode))
    app.add_handler(CallbackQueryHandler(menu_handler))
    print("✅ Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
