# Xray Vision Installer

🚀 **Xray-Vision-Installer** ialah skrip automasi penuh untuk memasang & mengurus server **Xray VLESS** dengan sokongan TLS dan Reality (stealth).  
Skrip ini membolehkan anda pilih antara **Direct TLS**, **Nginx Reverse Proxy**, atau **Reality Mode**, serta sokongan sijil **Standalone** atau **Cloudflare DNS API**.

---

## ✨ Ciri-ciri

- Pasang **Xray-core (latest release)**
- Pilihan mode connection:
  - **Direct TLS** → Xray handle TLS
  - **Nginx Reverse Proxy** → Xray backend, Nginx handle TLS
  - **Reality Mode** → Xray Reality, stealth, port 443 free, tanpa TLS
- Pilihan sijil:
  - **Standalone** → port 80 diperlukan semasa issuance
  - **Cloudflare DNS API** → port 80 tidak diperlukan
- Auto **Let's Encrypt certificate** melalui `acme.sh`
- Auto generate **UUID VLESS**
- Auto generate **VLESS URI + QR Code**
- **Tambah / Buang / Senarai pengguna (UUID)**
- **Backup & Restore konfigurasi**
- **Renew certificate automatik**
- Fungsi **Uninstall bersih**
- **Menu interaktif** (loop hingga exit)

---

# Domain & TLS Setup untuk Xray Vision Installer

Panduan ini menerangkan cara sediakan domain, TLS, dan Cloudflare API untuk installer Xray Vision 6-in-1.

---

## 1️⃣ Dapatkan Domain

Pergi ke laman pembekal domain popular seperti:

- Namecheap
- GoDaddy
- Cloudflare Registrar

1. Cari nama domain yang anda mahu, contoh: `myvpsserver.com`.
2. Daftar dan bayar untuk memiliki domain tersebut. Harga biasanya USD 1–15 / tahun bergantung TLD (.com, .net, .xyz dll).

---

## 2️⃣ Dapatkan VPS dan Catat IP

Sewa VPS daripada pembekal seperti:

- Vultr
- DigitalOcean
- Linode
- Hetzner
- AWS Lightsail

Pastikan:

- VPS siap dan anda dapat IP awam, contoh: `123.45.67.89`.
- Port 80 & 443 dibuka (firewall / security group).

---

## 3️⃣ Point Domain ke VPS (DNS A Record)

1. Login ke panel pengurusan domain (Namecheap/GoDaddy/Cloudflare).
2. Pergi ke **DNS Management / Zone Editor**.
3. Buat **A Record**:

| Name / Host | Value / Points to | TTL     |
|------------|-----------------|--------|
| @          | VPS IP (contoh: 123.45.67.89) | Default / 3600 |

Untuk subdomain, contohnya `vpn.myvpsserver.com`, buat A Record baru:

| Name | Value |
|------|-------|
| vpn  | VPS IP |

Tunggu propagasi DNS (5 minit – 24 jam).

---

## 4️⃣ Sahkan Domain Resolve

Di terminal / CMD:

```bash
ping myvpsserver.com
```

Pastikan IP yang keluar sama dengan IP VPS anda.

---

## 5️⃣ Nota untuk TLS

- **Standalone TLS**: domain perlu resolve ke IP VPS supaya acme.sh boleh verify dan keluarkan certificate.
- **Cloudflare TLS**: boleh guna DNS API, tak perlu port 80 terbuka, tapi perlukan `CF_Email` & `CF_Key`.
- **Reality Mode**: jika tiada domain, gunakan mode Reality (paling stealth, TLS bypass, port 443 bebas, tiada certificate sebenar).

---

## Cloudflare API untuk TLS

### 1️⃣ Daftar / Login Cloudflare

1. Pergi ke [Cloudflare](https://www.cloudflare.com)
2. Daftar akaun atau login.
3. Tambah domain ke Cloudflare (ikut wizard **Add a Site**).
4. Tukar **nameserver** di registrar supaya domain diuruskan Cloudflare.

### 2️⃣ Cari Global API Key

1. Klik **My Profile** (ikon user di kanan atas).
2. Pergi ke **API Tokens**.
3. Di bahagian **Global API Key**, klik **View**.
4. Masukkan kata laluan Cloudflare untuk sahkan.
5. Copy key → ini adalah `CF_Key`.

### 3️⃣ Dapatkan Email Cloudflare

Email yang digunakan akaun Cloudflare adalah `CF_Email`.  
Contoh: `user@mail.com`.

### 4️⃣ Simpan CF_Email & CF_Key di environment variable

Di terminal VPS:

```bash
export CF_Email="user@mail.com"
export CF_Key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Pastikan variable ini aktif sebelum jalankan installer.

### 5️⃣ Gunakan dalam Xray Installer

Pilih mode:

- Direct + Cloudflare  
- Nginx + Cloudflare  

Installer akan gunakan `CF_Email` & `CF_Key` untuk issue TLS certificate tanpa port 80 terbuka.

---

## 📥 Cara Install

Clone repo dan jalankan installer:

```bash
git clone https://github.com/racunzx/Xray-Vision-Installer.git
cd Xray-Vision-Installer
chmod +x xray-vision-installer.sh
sudo ./xray-vision-installer.sh
```

Skrip akan memaparkan **menu interaktif** untuk pilih mode dan fungsi.

---

## ⚙️ Kombinasi Versi & Kegunaan

| Mode / Versi        | TLS Handler | SSL Method           | Port 80 diperlukan? | Kegunaan |
|--------------------|------------|--------------------|-------------------|----------|
| Direct + Standalone | Xray       | Standalone (acme.sh) | ✅ Ya | VPS kosong, setup simple |
| Direct + CF DNS API | Xray       | Cloudflare API       | ❌ Tidak | VPS dengan port 80 terhalang |
| Nginx + Standalone  | Nginx      | Standalone (acme.sh) | ✅ Ya | Combine web + VPN |
| Nginx + CF DNS API  | Nginx      | Cloudflare API       | ❌ Tidak | Production + web + VPN + Cloudflare |
| Direct + Reality    | Xray       | Tiada TLS            | ❌ Tidak | Paling baru, stealth, port 443 free |
| Nginx + Reality     | Nginx      | Tiada TLS            | ❌ Tidak | Gabungkan web + Xray Reality (stealth) |

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

## 📝 Fungsi Menu

1. **Install Xray Server** → Pilih mode, TLS, sijil, dan skrip akan setup Xray + Nginx/Reality.
2. **Add User** → Tambah UUID baru untuk pelanggan.
3. **List Users** → Senarai UUID yang telah dibuat.
4. **Remove User** → Buang UUID tertentu.
5. **Renew Certificate** → Auto renew TLS certificate.
6. **Backup Config** → Backup folder Xray & SSL.
7. **Restore Config** → Restore dari backup.
8. **Show Log** → Papar log terakhir.
9. **Uninstall** → Remove Xray & config sepenuhnya.
0. **Exit** → Keluar dari menu.

---

## ⚡ Nota

- **Reality Mode** memerlukan port 443 kosong, tanpa TLS, lebih stealth.
- Cloudflare API sesuai jika port 80 blocked.
- Standalone mode perlukan port 80 terbuka semasa issuance cert.

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

