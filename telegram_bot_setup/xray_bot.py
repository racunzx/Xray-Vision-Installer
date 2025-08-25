#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot: Xray/VLESS Manager (Inline Menu) — UPGRADE
Author  : racunzx
Repo    : https://github.com/racunzx/Xray-Vision-Installer
Version : 2.0 (inject config + auto-expire + traffic)
"""

import os
import io
import json
import uuid
import qrcode
import shutil
import subprocess
from datetime import datetime, timedelta

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue
)

# ----------------- Env / Paths -----------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_USER_ID", "0"))

XRAY_DIR = "/etc/xray"
CONFIG_FILE = f"{XRAY_DIR}/config.json"
USERS_FILE  = f"{XRAY_DIR}/users.json"
DOMAIN_FILE = f"{XRAY_DIR}/domain.json"

# API server (untuk xray api statsquery). Jika anda set lain, ubah sini.
XRAY_API_ADDR = "127.0.0.1:10085"

os.makedirs(XRAY_DIR, exist_ok=True)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f: json.dump({}, f)
if not os.path.exists(DOMAIN_FILE):
    with open(DOMAIN_FILE, "w") as f: json.dump({"domain": "", "mode": "direct"}, f)

# ----------------- Util -----------------
def is_admin(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else 0
    return uid == ADMIN_ID

def load_json(path: str, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception:
        return default

def save_json(path: str, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f: json.dump(data, f, indent=2)
    shutil.move(tmp, path)

def load_users():  return load_json(USERS_FILE, {})
def save_users(d): save_json(USERS_FILE, d)

def load_domain():  return load_json(DOMAIN_FILE, {"domain": "", "mode": "direct"})
def save_domain(d): save_json(DOMAIN_FILE, d)

def generate_uuid() -> str:
    return str(uuid.uuid4())

def restart_xray():
    subprocess.run("systemctl restart xray", shell=True)

def restart_nginx():
    subprocess.run("systemctl restart nginx", shell=True)

def qrcode_png(data: str) -> io.BytesIO:
    img = qrcode.make(data)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def dt_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def today() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# ----------------- Xray Config Helpers -----------------
def load_config():
    return load_json(CONFIG_FILE, {})

def save_config(cfg):
    save_json(CONFIG_FILE, cfg)

def ensure_stats_enabled(cfg: dict) -> dict:
    # Tambah blok API/Stats/Policy jika tiada (wajib untuk trafik per user)
    if "api" not in cfg:
        cfg["api"] = {"services": ["StatsService"]}
    else:
        svcs = set(cfg["api"].get("services", []))
        svcs.add("StatsService")
        cfg["api"]["services"] = list(svcs)

    if "stats" not in cfg:
        cfg["stats"] = {}

    # Pastikan policy enable stats
    if "policy" not in cfg:
        cfg["policy"] = {"levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}}}
    else:
        levels = cfg["policy"].get("levels", {})
        level0 = levels.get("0", {})
        level0["statsUserUplink"] = True
        level0["statsUserDownlink"] = True
        levels["0"] = level0
        cfg["policy"]["levels"] = levels

    # Pastikan dok 'inbounds' wujud
    if "inbounds" not in cfg or not isinstance(cfg["inbounds"], list):
        cfg["inbounds"] = []
    return cfg

def find_vless_inbound(cfg: dict) -> int:
    """Cari index inbound VLESS utama (pertama dijumpai)."""
    for i, ib in enumerate(cfg.get("inbounds", [])):
        if ib.get("protocol") == "vless":
            return i
    return -1

def get_clients_list(cfg: dict):
    idx = find_vless_inbound(cfg)
    if idx == -1: return None, None
    ib = cfg["inbounds"][idx]
    clients = ib.get("settings", {}).get("clients", None)
    return idx, clients

def add_client_to_config(user_id: str, uuid_str: str) -> bool:
    cfg = ensure_stats_enabled(load_config())
    ib_idx = find_vless_inbound(cfg)
    if ib_idx == -1:
        return False
    ib = cfg["inbounds"][ib_idx]
    settings = ib.setdefault("settings", {})
    clients = settings.setdefault("clients", [])
    # Jangan duplicate email/uuid
    for c in clients:
        if c.get("email") == user_id or c.get("id") == uuid_str:
            return True
    clients.append({
        "id": uuid_str,
        "flow": "xtls-rprx-vision",
        "email": user_id
    })
    save_config(cfg)
    return True

def remove_client_from_config(user_id: str) -> bool:
    cfg = load_config()
    ib_idx, clients = get_clients_list(cfg)
    if ib_idx is None or clients is None:
        return False
    new_clients = [c for c in clients if c.get("email") != user_id]
    cfg["inbounds"][ib_idx]["settings"]["clients"] = new_clients
    save_config(cfg)
    return True

# ----------------- Link Builder -----------------
def build_vless_link(user_id: str, uuid_str: str, domain: str, mode: str) -> str:
    # Kekalkan jenis TCP Vision (ikut installer)
    if mode == "nginx":
        # Di nginx, Xray back-end TCP; link tetap TCP TLS (client nampak domain:443 TLS)
        return f"vless://{uuid_str}@{domain}:443?encryption=none&security=tls&type=tcp&flow=xtls-rprx-vision&sni={domain}#xray-{user_id}"
    else:
        return f"vless://{uuid_str}@{domain}:443?encryption=none&security=tls&type=tcp&flow=xtls-rprx-vision&sni={domain}#xray-{user_id}"

# ----------------- Traffic via Xray API -----------------
def bytes_fmt(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"

def query_user_traffic(email: str) -> tuple[int, int]:
    """
    Xray stats per-user berdasarkan 'email' pada client.
    Nama metrik:
      user>>>EMAIL>>>traffic>>>uplink
      user>>>EMAIL>>>traffic>>>downlink
    """
    def _q(name: str) -> int:
        cmd = f'xray api statsquery --server={XRAY_API_ADDR} --name "{name}"'
        try:
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True).strip()
            # Output biasanya integer bytes; jika tidak, cuba parse json / fallback 0
            if out.isdigit():
                return int(out)
            # cuba parse jika format lain
            try:
                j = json.loads(out)
                # sokong format {"name":"","value":123}
                if isinstance(j, dict) and "value" in j:
                    return int(j["value"])
            except Exception:
                pass
            return int(float(out))
        except Exception:
            return 0

    up = _q(f"user>>>{email}>>>traffic>>>uplink")
    dn = _q(f"user>>>{email}>>>traffic>>>downlink")
    return up, dn

# ----------------- Expiry Job -----------------
async def job_expiry_check(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    changed = False
    removed = []
    for user_id, meta in list(users.items()):
        exp_str = meta.get("expired", "")
        try:
            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
        except Exception:
            # tiada tarikh → anggap tamat
            exp_dt = today() - timedelta(days=1)
        if exp_dt < today():
            # padam dari config & users
            remove_client_from_config(user_id)
            users.pop(user_id, None)
            changed = True
            removed.append(user_id)
    if changed:
        save_users(users)
        restart_xray()
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"🧹 Auto-expire: dipadam {len(removed)} user: {', '.join(removed)}"
                )
            except Exception:
                pass

# ----------------- UI (Inline Menu) -----------------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Status Server", callback_data="status")],
        [InlineKeyboardButton("👥 Senarai User", callback_data="list")],
        [
            InlineKeyboardButton("➕ Tambah User", callback_data="add"),
            InlineKeyboardButton("❌ Padam User", callback_data="del")
        ],
        [
            InlineKeyboardButton("🔑 Renew User", callback_data="renew"),
            InlineKeyboardButton("📈 Trafik User", callback_data="trafik")
        ],
        [
            InlineKeyboardButton("🔄 Restart Service", callback_data="restart"),
            InlineKeyboardButton("⚙️ Info Config", callback_data="info")
        ],
        [InlineKeyboardButton("📜 Log Xray", callback_data="logs")]
    ])

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Kembali ke Menu Utama", callback_data="back")]])

# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text("🤖 Xray Manager — pilih menu:", reply_markup=main_menu())

async def handle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "back":
        await q.edit_message_text("↩️ Menu Utama", reply_markup=main_menu())
        return

    if data == "status":
        xray = subprocess.getoutput("systemctl is-active xray")
        nginx = subprocess.getoutput("systemctl is-active nginx")
        msg = f"📊 Status:\n- Xray : {xray}\n- Nginx: {nginx}"
        await q.edit_message_text(msg, reply_markup=back_menu())
        return

    if data == "info":
        d = load_domain()
        cfg = load_config()
        ib_idx = find_vless_inbound(cfg)
        port = cfg.get("inbounds", [{}])[ib_idx].get("port") if ib_idx != -1 else "?"
        msg = f"⚙️ Config Ringkas\n- Domain: {d.get('domain','')}\n- Mode: {d.get('mode','direct')}\n- Inbound port: {port}\n- API: {XRAY_API_ADDR}"
        await q.edit_message_text(msg, reply_markup=back_menu())
        return

    if data == "logs":
        logs = subprocess.getoutput("journalctl -u xray --no-pager -n 50")
        # potong jika terlalu panjang
        logs = logs[-3500:]
        await q.edit_message_text(f"📜 Log Xray (50 baris):\n{logs}", reply_markup=back_menu())
        return

    if data == "list":
        users = load_users()
        if not users:
            await q.edit_message_text("👥 Tiada user.", reply_markup=back_menu())
            return
        lines = []
        for u, m in users.items():
            lines.append(f"- {u} | UUID: {m['uuid'][:8]}… | Exp: {m['expired']}")
        await q.edit_message_text("👥 Senarai User:\n" + "\n".join(lines), reply_markup=back_menu())
        return

    if data == "add":
        users = load_users()
        # cipta ID unik
        base = "user"
        i = 1
        while f"{base}{i}" in users:
            i += 1
        user_id = f"{base}{i}"
        uid = generate_uuid()
        exp = dt_str(datetime.now() + timedelta(days=30))
        # inject ke config
        ok = add_client_to_config(user_id, uid)
        if not ok:
            await q.edit_message_text("❌ Gagal tambah ke config (tiada inbound VLESS?).", reply_markup=back_menu())
            return
        # simpan metadata user
        users[user_id] = {
            "uuid": uid,
            "created": dt_str(datetime.now()),
            "expired": exp
        }
        save_users(users)
        restart_xray()

        d = load_domain()
        link = build_vless_link(user_id, uid, d["domain"], d.get("mode","direct"))
        img = qrcode_png(link)
        await q.message.reply_photo(InputFile(img, filename="vless.png"),
                                    caption=f"✅ User **{user_id}** ditambah\nExp: {exp}\n\n`{link}`",
                                    parse_mode="Markdown")
        await q.edit_message_text("User ditambah. ", reply_markup=back_menu())
        return

    if data == "del":
        users = load_users()
        if not users:
            await q.edit_message_text("❌ Tiada user.", reply_markup=back_menu())
            return
        keys = sorted(users.keys())
        rows = [[InlineKeyboardButton(k, callback_data=f"del:{k}") ] for k in keys]
        rows.append([InlineKeyboardButton("↩️ Kembali", callback_data="back")])
        await q.edit_message_text("Pilih user untuk dipadam:", reply_markup=InlineKeyboardMarkup(rows))
        return

    if data.startswith("del:"):
        user_id = data.split(":",1)[1]
        users = load_users()
        if user_id in users:
            remove_client_from_config(user_id)
            users.pop(user_id, None)
            save_users(users)
            restart_xray()
            await q.edit_message_text(f"✅ {user_id} dipadam.", reply_markup=back_menu())
        else:
            await q.edit_message_text("User tidak wujud.", reply_markup=back_menu())
        return

    if data == "renew":
        users = load_users()
        if not users:
            await q.edit_message_text("❌ Tiada user.", reply_markup=back_menu())
            return
        keys = sorted(users.keys())
        rows = [[InlineKeyboardButton(k, callback_data=f"renew:{k}") ] for k in keys]
        rows.append([InlineKeyboardButton("↩️ Kembali", callback_data="back")])
        await q.edit_message_text("Pilih user untuk renew +30 hari:", reply_markup=InlineKeyboardMarkup(rows))
        return

    if data.startswith("renew:"):
        user_id = data.split(":",1)[1]
        users = load_users()
        if user_id in users:
            users[user_id]["expired"] = dt_str(datetime.now() + timedelta(days=30))
            save_users(users)
            await q.edit_message_text(f"✅ {user_id} diperbaharui hingga {users[user_id]['expired']}.", reply_markup=back_menu())
        else:
            await q.edit_message_text("User tidak wujud.", reply_markup=back_menu())
        return

    if data == "trafik":
        users = load_users()
        if not users:
            await q.edit_message_text("❌ Tiada user.", reply_markup=back_menu())
            return
        keys = sorted(users.keys())
        rows = [[InlineKeyboardButton(k, callback_data=f"tfx:{k}")] for k in keys]
        rows.append([InlineKeyboardButton("↩️ Kembali", callback_data="back")])
        await q.edit_message_text("Pilih user untuk lihat trafik:", reply_markup=InlineKeyboardMarkup(rows))
        return

    if data.startswith("tfx:"):
        user_id = data.split(":",1)[1]
        up, dn = query_user_traffic(user_id)
        await q.edit_message_text(
            f"📈 Trafik **{user_id}**\n⬆️ Uplink  : {bytes_fmt(up)}\n⬇️ Downlink: {bytes_fmt(dn)}",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        return

    if data == "restart":
        restart_xray()
        restart_nginx()
        await q.edit_message_text("🔄 Xray & Nginx direstart.", reply_markup=back_menu())
        return

# ----------------- Commands -----------------
async def setdomain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setdomain <domain>")
        return
    d = load_domain()
    d["domain"] = context.args[0]
    save_domain(d)
    await update.message.reply_text(f"✅ Domain ditetapkan ke: {d['domain']}")

async def setmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    if len(context.args) != 1 or context.args[0] not in ["direct", "nginx"]:
        await update.message.reply_text("Usage: /setmode <direct|nginx>")
        return
    d = load_domain()
    d["mode"] = context.args[0]
    save_domain(d)
    await update.message.reply_text(f"✅ Mode ditetapkan ke: {d['mode']}")

async def forcecheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    await job_expiry_check(context)
    await update.message.reply_text("🧹 Semakan tamat tempoh dipaksa sekarang.")

# ----------------- Main -----------------
def main():
    if not BOT_TOKEN or ADMIN_ID == 0:
        print("ERR: TELEGRAM_BOT_TOKEN atau ADMIN_USER_ID tidak ditetapkan.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setdomain", setdomain))
    app.add_handler(CommandHandler("setmode", setmode))
    app.add_handler(CommandHandler("forcecheck", forcecheck))

    # Inline callbacks
    app.add_handler(CallbackQueryHandler(handle_cb))

    # Job auto-expire: setiap 1 jam
    jq: JobQueue = app.job_queue
    jq.run_repeating(job_expiry_check, interval=3600, first=30)

    print("✅ Xray Telegram Bot berjalan…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
