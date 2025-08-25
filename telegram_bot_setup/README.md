# Xray Telegram Manager Bot

Versi final ini membolehkan awak memantau dan mengurus server Xray/VLESS melalui **Telegram Bot** dengan menu inline, auto-start selepas reboot, dan logging.

---

## 1️⃣ Kandungan Repo

- **xray_bot.py** → Skrip bot Python yang:
  - Memantau status Xray/Nginx
  - Senarai/add/remove/renew user dengan UUID & expiry
  - Menunjukkan trafik user (via Xray API)
  - Restart service, tunjuk log, renew SSL
  - Config menu dummy & cleanup expired user
  - Semua menu inline, butang `↩️ Kembali ke Menu Utama`
  - Logging ke `bot.log` & console
  - Baca `TELEGRAM_BOT_TOKEN` dan `ADMIN_USER_ID` dari environment

- **installer.sh** → Skrip pemasangan automatik:
  - Sediakan folder `/opt/xraybot`
  - Download `xray_bot.py`
  - Pasang Python 3 virtualenv dan dependencies (`python-telegram-bot`, `qrcode`)
  - Minta token bot & admin ID semasa install
  - Simpan environment file `/etc/xray-bot.env`
  - Buat systemd service `/etc/systemd/system/xray-bot.service`
  - Auto-start & enable service
  - Bot berjalan di background & restart automatik jika crash
  - Log boleh diperiksa dengan `journalctl -u xray-bot.service -f`

---

## 2️⃣ Cara Pasang

Jalankan satu baris ini pada server (root / sudo):

```bash
sudo bash -c 'mkdir -p /opt/xraybot && cd /opt/xraybot && \
wget -O xray_bot.py https://raw.githubusercontent.com/racunzx/Xray-Vision-Installer/main/telegram_bot_setup/xray_bot.py && \
wget -O installer.sh https://raw.githubusercontent.com/racunzx/Xray-Vision-Installer/main/telegram_bot_setup/installer.sh && \
chmod +x installer.sh && ./installer.sh'
```

**Langkah installer:**
1. Masukkan `TELEGRAM_BOT_TOKEN` (dari BotFather)
2. Masukkan `ADMIN_USER_ID` (numeric Telegram ID)

Bot akan terus berjalan di background selepas install selesai.

---

## 3️⃣ Fungsi Bot

| Butang / Menu           | Fungsi                                                                 |
|------------------------|------------------------------------------------------------------------|
| 📊 Status Server        | Tunjuk uptime & status Xray/Nginx                                      |
| 👥 Senarai User         | Senarai semua user dengan tarikh expired                                |
| ➕ Tambah User           | Tambah user baru, auto generate UUID & expiry                           |
| ❌ Buang User           | Buang user terakhir atau pilih user dari list                            |
| 🔑 Renew User           | Renew expiry user                                                        |
| 📈 Trafik User          | Papar trafik user (Xray API)                                            |
| 🔄 Restart Service       | Restart Xray & Nginx                                                    |
| 🧾 Tunjuk Log           | Papar log terakhir Xray (journalctl)                                    |
| 🔐 Renew Sijil          | Renew SSL certificate (certbot / acme.sh)                               |
| ⚙️ Config / Set          | Config dummy, boleh extend untuk ubah domain, port, limit user           |
| 🧹 Cleanup Expired       | Buang user yang expired secara automatik                                 |
| ↩️ Kembali ke Menu Utama | Kembali ke menu utama                                                   |

---

## 4️⃣ Logging

- Semua aksi bot dicatat ke `bot.log` di folder `/opt/xraybot/`
- Debug & info dicatat juga ke console

---

## 5️⃣ Notes

- Bot perlu **root** supaya boleh edit `config.json` dan restart Xray
- Environment variables:
  ```bash
  TELEGRAM_BOT_TOKEN="xxxxx"
  ADMIN_USER_ID="xxxxxx"
  ```
- Bot auto-run selepas reboot
- Untuk cek status bot:
  ```bash
  systemctl status xray-bot.service
  journalctl -u xray-bot.service -f
  ```

---

## 6️⃣ Folder Struktur Selepas Install

```
/opt/xraybot/
├─ xray_bot.py
├─ installer.sh
├─ venv/
└─ bot.log
/etc/
└─ xray-bot.env
/etc/systemd/system/
└─ xray-bot.service
```

---

## 7️⃣ Cara Remove Bot

```bash
systemctl stop xray-bot.service
systemctl disable xray-bot.service
rm -rf /opt/xraybot
rm /etc/systemd/system/xray-bot.service
rm /etc/xray-bot.env
systemctl daemon-reload
```

Selesai! Bot sekarang boleh monitor & manage server Xray terus melalui Telegram.

## 📜 License

MIT License © 2025 [racunzx](https://github.com/racunzx)

---

## 🙏 Credits

- [Xray-core](https://github.com/XTLS/Xray-core)  
- [acme.sh](https://github.com/acmesh-official/acme.sh)  
- Builder: **racunzx**

