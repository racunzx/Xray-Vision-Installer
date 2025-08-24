# Xray Vision Installer

Script auto-installer untuk setup **Xray (VLESS + Vision + TLS)** di server Ubuntu (contoh: DigitalOcean, Vultr, AWS, dsb).  
Direka khas untuk **bypass sekatan ISP**, **lindungi privasi**, dan kelihatan seperti trafik HTTPS biasa (stealth mode).

---

## ✨ Features
- Support dua mode install:
  - **Standalone** (Xray + TLS)
  - **Cloudflare CDN** (Xray + TLS + CDN)
- Auto generate domain SSL dengan **acme.sh**
- Konfigurasi automatik untuk **Nginx + Xray**
- Trafik nampak macam HTTPS normal → susah dikesan (anti-DPI)
- Sesuai untuk **Android (v2rayNG), iOS (Shadowrocket), Windows/Mac/Linux (Xray-core client)**

---

## 📦 Requirement
- Server **Ubuntu 20.04 / 22.04 / 24.04** (tested on DigitalOcean)
- Domain/subdomain yang point ke IP server
- Akses root (`sudo`)

---

## 🚀 Installation
1. Clone repo & masuk folder:
   ```bash
   git clone https://github.com/racunzx/Xray-Vision-Installer.git
   cd xray-vision-installer
   chmod +x xray-vision-installer.sh
   ```

2. Jalankan installer:
   ```bash
   ./xray-vision-installer.sh
   ```

3. Pilih mode install:
   - Standalone  
   - Cloudflare

---

## 🔑 Output
Selepas install berjaya, script akan bagi:
- UUID user
- Domain
- Port (default 443)
- Link VLESS siap untuk import ke **v2rayNG / Shadowrocket / Xray client**

---

## 📱 Client Example (Android v2rayNG)
1. Buka app **v2rayNG**
2. Klik `+` → `Import from clipboard`
3. Paste link yang script bagi
4. Connect & enjoy 🚀

---

## 🔒 Security
- Auto SSL renew by **acme.sh** (default cronjob)
- Semua trafik encrypted (TLS 1.3)
- Vision protocol → menyamar jadi HTTPS biasa

---

## ⚠️ Disclaimer
Script ini untuk **pembelajaran & kegunaan peribadi sahaja**.  
Gunakan dengan tanggungjawab masing-masing.
