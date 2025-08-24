# Xray Vision Installer

🚀 **Xray-Vision-Installer** ialah skrip automasi penuh untuk memasang & mengurus server **Xray VLESS** dengan sokongan TLS.  
Skrip ini membolehkan anda pilih sama ada **Direct TLS** atau **Nginx Reverse Proxy**, serta sokongan sijil **Standalone** atau **Cloudflare DNS API**.

---

## ✨ Features

- Pasang **Xray-core (latest release)**
- Pilihan **Direct TLS** atau **Nginx Reverse Proxy**
- Pilihan sijil:
  - Standalone (port 80 terbuka)
  - Cloudflare DNS API (tanpa gangguan port 80)
- Auto **Let's Encrypt certificate** melalui `acme.sh`
- Auto generate **UUID VLESS**
- Auto generate **VLESS URI + QR Code**
- Konfigurasi **systemd** (Xray auto start & survive reboot)
- Fungsi **Uninstall** (bersih penuh)

---

## 📥 Cara Install

Clone repo dan jalankan installer:

```bash
git clone https://github.com/racunzx/Xray-Vision-Installer.git
cd Xray-Vision-Installer
chmod +x xray-vision-installer.sh
./xray-vision-installer.sh install
```

---

## ⚙️ Pilihan Mode

Semasa install, anda akan ditanya:

1. **Connection Mode**
   - `Direct` → Xray terus handle TLS  
   - `Nginx` → Guna Nginx sebagai reverse proxy  

2. **Certificate Mode**
   - `Standalone` → Guna port 80 untuk issue cert  
   - `Cloudflare` → Guna API Cloudflare (tak perlu open port 80)  

---

## 🔑 Output Selepas Install

Selepas berjaya install, skrip akan papar:

- **UUID (User ID)**
- **Domain**
- **VLESS URI** (boleh import ke client seperti v2rayN / v2rayNG / Clash)
- **QR Code** (scan terus dari client)

Contoh URI:

```
vless://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx@domain.com:443?encryption=none&security=tls&type=ws&host=domain.com&path=%2F#Xray-Vision
```

---

## ❌ Uninstall

Untuk remove Xray & config sepenuhnya:

```bash
./xray-vision-installer.sh uninstall
```

---

## 📝 Requirements

- VPS / Cloud server (Ubuntu/Debian recommended)
- Domain sudah pointing ke IP server
- (Opsyenal) Cloudflare API key jika guna mode `Cloudflare`

---

## 📜 License

MIT License © 2025 [racunzx](https://github.com/racunzx)

---

## 🙏 Credits

- [Xray-core](https://github.com/XTLS/Xray-core)
- [acme.sh](https://github.com/acmesh-official/acme.sh)
- Builder: **racunzx**
