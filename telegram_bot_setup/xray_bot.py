#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot: Xray/VLESS Manager (Inline Menu + Manual Expiry)
Author  : racunzx
Version : 2.0 final
"""

import os
import json
import logging
import subprocess
from datetime import datetime, timedelta
from uuid import uuid4

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# =====================
# Logging
# =====================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# =====================
# Config
# =====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_USER_ID", "0"))
CONFIG_PATH = "/etc/xray/config.json"

# =====================
# Conversation States
# =====================
WAIT_EXPIRY = 1

# =====================
# Helpers
# =====================
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def restart_xray():
    subprocess.run(["systemctl", "restart", "xray"], check=False)
    logger.info("Xray service restarted.")

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

# =====================
# Handlers
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("Selamat datang, Admin ✅", reply_markup=main_menu_markup())

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return
    action = query.data

    cfg = load_config()

    # --- Status ---
    if action == "status":
        uptime = subprocess.getoutput("uptime -p")
        await query.edit_message_text(f"📊 Status Server:\n{uptime}", reply_markup=main_menu_markup())

    # --- List Users ---
    elif action == "list":
        users = []
        for inbound in cfg.get("inbounds", []):
            for c in inbound.get("settings", {}).get("clients", []):
                exp = c.get("expiryTime","N/A")
                users.append(f"- {c.get('email','?')} (exp: {exp})")
        text = "\n".join(users) if users else "Tiada user."
        await query.edit_message_text(f"👥 Senarai User:\n{text}", reply_markup=main_menu_markup())

    # --- Add User (manual expiry) ---
    elif action == "add":
        await query.message.reply_text("Masukkan tempoh expiry untuk user baru (dalam hari):")
        return WAIT_EXPIRY

    # --- Remove User ---
    elif action == "remove":
        if cfg["inbounds"][0]["settings"]["clients"]:
            removed = cfg["inbounds"][0]["settings"]["clients"].pop()
            save_config(cfg)
            restart_xray()
            await query.edit_message_text(f"❌ User dibuang:\n{removed}", reply_markup=main_menu_markup())
        else:
            await query.edit_message_text("❌ Tiada user untuk dibuang.", reply_markup=main_menu_markup())

    # --- Renew User ---
    elif action == "renew":
        if cfg["inbounds"][0]["settings"]["clients"]:
            user = cfg["inbounds"][0]["settings"]["clients"][-1]
            user["expiryTime"] = (datetime.now() + timedelta(days=30)).isoformat()
            save_config(cfg)
            restart_xray()
            await query.edit_message_text(f"🔑 User renewed:\n{user}", reply_markup=main_menu_markup())
        else:
            await query.edit_message_text("❌ Tiada user untuk renew.", reply_markup=main_menu_markup())

    # --- Traffic ---
    elif action == "traffic":
        output = subprocess.getoutput("xray api statsquery --server=127.0.0.1:10085")
        await query.edit_message_text(f"📈 Trafik User:\n{output}", reply_markup=main_menu_markup())

    # --- Restart Service ---
    elif action == "restart":
        restart_xray()
        await query.edit_message_text("🔄 Xray restarted.", reply_markup=main_menu_markup())

    # --- Show Logs ---
    elif action == "logs":
        logs = subprocess.getoutput("journalctl -u xray --no-pager -n 20")
        await query.edit_message_text(f"🧾 Log Terbaru:\n{logs}", reply_markup=main_menu_markup())

    # --- Renew Cert ---
    elif action == "renew_cert":
        out = subprocess.getoutput("certbot renew --quiet")
        await query.edit_message_text(f"🔐 Cert renewed:\n{out}", reply_markup=main_menu_markup())

    # --- Config / Set ---
    elif action == "config":
        await query.edit_message_text("⚙️ Config menu (dummy).", reply_markup=main_menu_markup())

    # --- Cleanup Expired ---
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
        await query.edit_message_text(f"🧹 Cleanup: {before-after} user expired dibuang.", reply_markup=main_menu_markup())

    # --- Back to main ---
    elif action == "home":
        await query.edit_message_text("↩️ Kembali ke menu utama.", reply_markup=main_menu_markup())

    return ConversationHandler.END

# --- Receive manual expiry ---
async def receive_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Sila masukkan nombor sahaja.")
        return WAIT_EXPIRY

    cfg = load_config()
    clients = cfg["inbounds"][0]["settings"]["clients"]

    new_user = {
        "id": str(uuid4()),
        "email": f"user{int(datetime.now().timestamp())}@bot",
        "expiryTime": (datetime.now() + timedelta(days=days)).isoformat()
    }
    clients.append(new_user)
    save_config(cfg)
    restart_xray()

    await update.message.reply_text(
        f"✅ User {new_user['email']} ditambah\nExpiry: {days} hari ({new_user['expiryTime']})",
        reply_markup=main_menu_markup()
    )
    return ConversationHandler.END

# =====================
# Main
# =====================
def main():
    if not BOT_TOKEN or not ADMIN_ID:
        logger.error("BOT_TOKEN / ADMIN_ID tidak ditemui di env.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^add$")],
        states={
            WAIT_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_expiry)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
