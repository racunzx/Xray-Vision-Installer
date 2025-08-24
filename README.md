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

🔹 1. Direct + Standalone (port 80)
Fungsi:

Xray terus handle TLS/SSL (tak perlu Nginx).

Cert dikeluarkan guna acme.sh standalone → perlukan port 80 kosong masa issuance.

Sesuai untuk server kosong (tiada web server lain).

Setup paling ringkas → Xray terus listen 443.

📌 Kegunaan: untuk server kecil/VPS khas VPN, tak ada website.

🔹 2. Direct + Cloudflare DNS API
Fungsi:

Xray handle TLS/SSL (sama macam Direct).

Cert dikeluarkan melalui Cloudflare DNS API → tak perlukan port 80.

Boleh issue/renew SSL walaupun port 80 sudah dipakai atau firewall block.

Lebih reliable untuk server production dengan Cloudflare DNS.

📌 Kegunaan: sesuai kalau ada sekatan port 80 atau nak auto-renew cert tanpa ganggu service.

🔹 3. Nginx + Standalone (port 80)
Fungsi:

Nginx handle TLS/SSL dan jadi reverse proxy.

Cert dikeluarkan guna acme.sh standalone → perlukan port 80 kosong masa issuance.

Xray hanya listen di localhost (127.0.0.1:10000) tanpa TLS.

Sesuai kalau nak run website + VPN dalam 1 server.

📌 Kegunaan: bila nak combine web server (Nginx serve web, Xray jadi backend).

🔹 4. Nginx + Cloudflare DNS API
Fungsi:

Nginx handle TLS/SSL.

Cert dikeluarkan melalui Cloudflare DNS API → tak perlukan port 80.

Sangat stabil sebab auto-renew SSL boleh dibuat tanpa hentikan service.

Xray jalan di localhost (127.0.0.1:10000).

Sesuai untuk production server (website + VPN) dengan Cloudflare.

📌 Kegunaan: setup paling profesional, boleh integrate website (Nginx) + VPN (Xray) + Cloudflare dengan mudah.

## 🟢 Ringkasan beza 4 versi

| Mode                 | TLS Handler | SSL Method           | Port 80 diperlukan? | Kegunaan                               |
|-----------------------|-------------|----------------------|---------------------|----------------------------------------|
| **Direct + Standalone** | Xray        | Standalone (acme.sh) | ✅ Ya               | VPS kosong, setup paling simple         |
| **Direct + CF DNS API** | Xray        | Cloudflare API       | ❌ Tidak            | VPS dengan port 80 terhalang           |
| **Nginx + Standalone**  | Nginx       | Standalone (acme.sh) | ✅ Ya               | Combine web + VPN dalam 1 server       |
| **Nginx + CF DNS API**  | Nginx       | Cloudflare API       | ❌ Tidak            | Production setup: web + VPN + Cloudflare|


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
