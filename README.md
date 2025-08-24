# Xray Vision Installer 

🚀 **Xray-Vision-Installer** ialah skrip automasi penuh untuk memasang & mengurus server **Xray VLESS** dengan sokongan TLS.  
Skrip ini menyokong **Direct TLS** atau **Nginx Reverse Proxy**, serta **Standalone** atau **Cloudflare DNS API**. Skrip juga hadir dengan **menu** untuk manage user, backup/restore, renew cert, dan uninstall.

---

## ✨ Features

- Pasang **Xray-core (latest release)**
- Pilihan deploy:
  - `Direct TLS` → Xray handle TLS
  - `Nginx Reverse Proxy` → Xray backend, Nginx handle TLS
- Pilihan certificate:
  - Standalone (port 80 diperlukan semasa issuance)
  - Cloudflare DNS API (port 80 tidak diperlukan)
- Auto **Let's Encrypt cert** melalui `acme.sh`
- Auto generate **UUID VLESS**
- Auto generate **VLESS URI + QR Code**
- Add / Remove / List users (UUID)
- Backup & Restore konfigurasi
- Renew certificate automatik
- Fungsi **Uninstall** bersih
- Support menu interaktif (loop until exit)

---

## 📥 Cara Install

Clone repo dan jalankan skrip:

```bash
git clone https://github.com/racunzx/Xray-Vision-Installer.git
cd Xray-Vision-Installer
chmod +x xray-vision-installer.sh
./xray-vision-installer.sh
```

Skrip akan paparkan **menu interaktif**:

```
==========================================
      Xray Vision Installer - racunzx
==========================================
1) Install Xray Server
2) Add User
3) List Users
4) Remove User
5) Renew Certificate
6) Backup Config
7) Restore Config
8) Show Log
9) Uninstall
0) Exit
```

---

## ⚙️ Pilihan Mode Semasa Install

Semasa install, pilih deploy mode:

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

### 🔹 Kombinasi & Kegunaan

| Mode                | TLS Handler | SSL Method           | Port 80 diperlukan? | Kegunaan                            |
| ------------------- | ----------- | -------------------- | ------------------- | ----------------------------------- |
| Direct + Standalone | Xray        | Standalone (acme.sh) | ✅ Ya               | VPS kosong, setup simple            |
| Direct + CF DNS API | Xray        | Cloudflare API       | ❌ Tidak            | VPS dengan port 80 terhalang        |
| Nginx + Standalone  | Nginx       | Standalone (acme.sh) | ✅ Ya               | Combine web + VPN                   |
| Nginx + CF DNS API  | Nginx       | Cloudflare API       | ❌ Tidak            | Production + web + VPN + Cloudflare |

---

## 🔑 Fungsi Menu

1. **Install Xray Server** → Install dan konfigurasi Xray + TLS/Reverse Proxy  
2. **Add User** → Tambah UUID baru untuk client  
3. **List Users** → Papar semua UUID yang ada  
4. **Remove User** → Buang UUID tertentu  
5. **Renew Certificate** → Renew TLS cert via acme.sh  
6. **Backup Config** → Backup konfigurasi + cert  
7. **Restore Config** → Restore dari backup  
8. **Show Log** → Papar 30 baris log terakhir  
9. **Uninstall** → Remove Xray + Nginx config + cert sepenuhnya  

---

## 🔗 Output Selepas Install

- **UUID (User ID)**
- **Domain**
- **VLESS URI** (boleh import ke client: v2rayN / v2rayNG / Clash)
- **QR Code** (scan terus)

Contoh URI:

```
vless://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx@domain.com:443?encryption=none&security=tls&type=ws&host=domain.com&path=%2F#Xray-Vision
```

---

## ❌ Uninstall

Pilih menu `Uninstall` untuk remove Xray sepenuhnya:

```
./xray-vision-installer.sh
# lalu pilih 9) Uninstall
```

---

## 📝 Requirements

- VPS / Cloud server (Ubuntu/Debian recommended)  
- Domain sudah pointing ke IP server  
- (Opsyenal) Cloudflare API key jika guna mode `Cloudflare DNS API`  

---

## 📜 License

MIT License © 2025 [racunzx](https://github.com/racunzx)

---

## 🙏 Credits

- [Xray-core](https://github.com/XTLS/Xray-core)  
- [acme.sh](https://github.com/acmesh-official/acme.sh)  
- Builder: **racunzx**

