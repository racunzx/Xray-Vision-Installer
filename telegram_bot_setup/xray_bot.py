#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xray/VLESS Manager Telegram Bot - Final
Author: racunzx
Version: 1.0 final
"""

import os, json, logging, subprocess, io
from datetime import datetime, timedelta
from uuid import uuid4
import qrcode

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ----------------------
# Logging
# ----------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("/var/log/xray_bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ----------------------
# Config / Env
# ----------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_USER_ID", "0"))
CONFIG_PATH = "/etc/xray/config.json"

# ----------------------
# Helpers
# ----------------------
def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except:
        logger.error("Gagal load config.json")
        return {"inbounds":[{"settings":{"clients":[]}}]}

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def restart_xray():
    subprocess.run(["systemctl", "restart", "xray"], check=False)
    logger.info("Xray service restarted.")

def gen_qr(link: str) -> io.BytesIO:
    img = qrcode.make(link)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def main_menu_markup() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📊 Status Server", callback_data="status"),
         InlineKeyboardButton("👥 Senarai User", callback_data="list")],
        [InlineKeyboardButton("➕ Tambah User", callback_data="add"),
         InlineKeyboardButton("❌ Buang User", callback_data="remove")],
        [InlineKeyboardButton("🔑 Renew User", callback_data="renew"),
         InlineKeyboardButton("📈 Trafik User", callback_data="traffic")],
        [InlineKeyboardButton("🔄 Restart Service", callback_data="restart"),
         InlineKeyboardButton("🧾 Tunjuk Log", callback_data="logs")],
        [InlineKeyboardButton("🔐 Renew Sijil", callback_data="renew_cert"),
         InlineKeyboardButton("⚙️ Config / Set", callback_data="config")],
        [InlineKeyboardButton("🧹 Cleanup Expired", callback_data="cleanup")],
        [InlineKeyboardButton("↩️ Kembali ke Menu Utama", callback_data="home")]
    ]
    return InlineKeyboardMarkup(rows)

# ----------------------
# Handlers
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("Selamat datang, Admin ✅", reply_markup=main_menu_markup())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    cfg = load_config()
    action = query.data

    if action == "status":
        uptime = subprocess.getoutput("uptime -p")
        await query.edit_message_text(f"📊 Status Server:\n{uptime}", reply_markup=main_menu_markup())

    elif action == "list":
        users = []
        for c in cfg["inbounds"][0]["settings"]["clients"]:
            exp = c.get("expiryTime", "N/A")
            users.append(f"- {c.get('email','?')} (exp: {exp})")
        text = "\n".join(users) if users else "Tiada user."
        await query.edit_message_text(f"👥 Senarai User:\n{text}", reply_markup=main_menu_markup())

    elif action == "add":
        await query.edit_message_text("➕ Masukkan tempoh expiry (hari) untuk user baru, contoh 1/10/120:")
        context.user_data["awaiting_expiry"] = True

    elif action == "remove":
        if cfg["inbounds"][0]["settings"]["clients"]:
            removed = cfg["inbounds"][0]["settings"]["clients"].pop()
            save_config(cfg)
            restart_xray()
            await query.edit_message_text(f"❌ User dibuang:\n{removed}", reply_markup=main_menu_markup())
        else:
            await query.edit_message_text("❌ Tiada user untuk dibuang.", reply_markup=main_menu_markup())

    elif action == "renew":
        if cfg["inbounds"][0]["settings"]["clients"]:
            user = cfg["inbounds"][0]["settings"]["clients"][-1]
            user["expiryTime"] = (datetime.now() + timedelta(days=30)).isoformat()
            save_config(cfg)
            restart_xray()
            await query.edit_message_text(f"🔑 User renewed:\n{user}", reply_markup=main_menu_markup())
        else:
            await query.edit_message_text("❌ Tiada user untuk renew.", reply_markup=main_menu_markup())

    elif action == "traffic":
        try:
            output = subprocess.getoutput("xray api statsquery --server=127.0.0.1:10085")
        except:
            output = "❌ Trafik: API tidak aktif atau gagal."
        await query.edit_message_text(f"📈 Trafik User:\n{output}", reply_markup=main_menu_markup())

    elif action == "restart":
        restart_xray()
        await query.edit_message_text("🔄 Xray restarted.", reply_markup=main_menu_markup())

    elif action == "logs":
        logs = subprocess.getoutput("journalctl -u xray --no-pager -n 20")
        await query.edit_message_text(f"🧾 Log Terbaru:\n{logs[-3000:]}", reply_markup=main_menu_markup())

    elif action == "renew_cert":
        out = subprocess.getoutput("certbot renew --quiet")
        await query.edit_message_text(f"🔐 Cert renewed:\n{out}", reply_markup=main_menu_markup())

    elif action == "config":
        await query.edit_message_text("⚙️ Config / Set menu (dummy sekarang)", reply_markup=main_menu_markup())

    elif action == "cleanup":
        now = datetime.now()
        before = len(cfg["inbounds"][0]["settings"]["clients"])
        cfg["inbounds"][0]["settings"]["clients"] = [
            u for u in cfg["inbounds"][0]["settings"]["clients"]
            if "expiryTime" not in u or datetime.fromisoformat(u["expiryTime"]) > now
        ]
        after = len(cfg["inbounds"][0]["settings"]["clients"])
        save_config(cfg)
        restart_xray()
        await query.edit_message_text(f"🧹 Cleanup: {before-after} expired user dibuang.", reply_markup=main_menu_markup())

    elif action == "home":
        await query.edit_message_text("↩️ Kembali ke menu utama.", reply_markup=main_menu_markup())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_expiry"):
        try:
            days = int(update.message.text)
            cfg = load_config()
            exp_date = (datetime.now() + timedelta(days=days)).isoformat()
            new_user = {
                "id": str(uuid4()),
                "email": f"user{int(datetime.now().timestamp())}@bot",
                "expiryTime": exp_date
            }
            cfg["inbounds"][0]["settings"]["clients"].append(new_user)
            save_config(cfg)
            restart_xray()
            await update.message.reply_text(f"✅ User ditambah:\n{new_user}", reply_markup=main_menu_markup())
            logger.info(f"User baru: {new_user}")
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal tambah user: {e}")
        finally:
            context.user_data["awaiting_expiry"] = False

# ----------------------
# Main
# ----------------------
def main():
    if not BOT_TOKEN or not ADMIN_ID:
        logger.error("BOT_TOKEN / ADMIN_ID tidak ditemui di env.")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
