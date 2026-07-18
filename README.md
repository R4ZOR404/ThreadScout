<div align="center">

```
████████╗██╗  ██╗██████╗ ███████╗ █████╗ ██████╗
╚══██╔══╝██║  ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗
   ██║   ███████║██████╔╝█████╗  ███████║██║  ██║
   ██║   ██╔══██║██╔══██╗██╔══╝  ██╔══██║██║  ██║
   ██║   ██║  ██║██║  ██║███████╗██║  ██║██████╔╝
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝

███████╗ ██████╗ ██████╗ ██╗   ██╗████████╗
██╔════╝██╔════╝██╔═══██╗██║   ██║╚══██╔══╝
███████╗██║     ██║   ██║██║   ██║   ██║
╚════██║██║     ██║   ██║██║   ██║   ██║
███████║╚██████╗╚██████╔╝╚██████╔╝   ██║
╚══════╝ ╚═════╝ ╚═════╝  ╚═════╝    ╚═╝
```

**Instagram Mutual Research Tool — Unlimited Edition**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Async-green?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Rich](https://img.shields.io/badge/Rich-Terminal%20UI-purple)](https://rich.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

## 📋 Deskripsi

**ThreadScout** adalah aplikasi terminal modern yang mengumpulkan **username dan link profil Instagram** dari posting Threads secara publik berdasarkan kata kunci. Pencarian berjalan **tanpa batas waktu** (unlimited) hingga pengguna menghentikannya dengan `Ctrl+C`.

> ⚠️ Hanya posting yang **mengandung username Instagram atau link Instagram** yang dikumpulkan. Posting tanpa referensi Instagram diabaikan.

---

## ✨ Fitur Utama

- ♾️ **Pencarian Unlimited** — Berjalan terus tanpa batas waktu hingga `Ctrl+C`
- ⚡ **10 Tab Paralel** — Pencarian super cepat dengan 10 browser tab sekaligus
- 🚫 **Resource Blocking** — Blokir gambar, font, CSS, dan ads untuk kecepatan maksimal
- 📸 **Hanya Instagram** — Output hanya berisi posting dengan username/link IG yang ditemukan
- 🔗 **Link Instagram** — Setiap hasil menyertakan link profil lengkap (https://instagram.com/username)
- 📊 **Live Dashboard** — Statistik real-time selama pencarian berlangsung
- 🔄 **Auto-Cycle** — Keyword diulang dan diacak setiap siklus untuk jangkauan global
- 📄 **Export CSV/Excel** — Ekspor hasil dengan format profesional
- 📝 **60+ Keyword** — Keyword default mencakup berbagai bahasa dan variasi
- 🛡️ **Error Handling** — Penanganan timeout, CAPTCHA, login wall otomatis

---

## 🛠️ Instalasi

### Prasyarat

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **pip** (biasanya sudah terinstall bersama Python)

### Langkah Instalasi

```bash
# 1. Clone repositori
git clone https://github.com/R4ZOR404/ThreadScout.git
cd ThreadScout

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install browser Chromium
playwright install chromium
```

---

## 🚀 Cara Menjalankan

```bash
python main.py
```

Kemudian pilih menu **1 — Start Search** untuk memulai pencarian unlimited.

### Opsi CLI

```bash
# Browser terlihat (debugging)
python main.py --no-headless

# Atur jumlah scroll per keyword
python main.py --scroll 10

# Bantuan
python main.py --help
```

---

## ⚡ Cara Kerja Pencarian

1. **Start** → Pilih menu 1, konfirmasi `y`
2. **Running** → 10 tab browser dibuka secara paralel, mencari keyword secara bersamaan
3. **Filtering** → Hanya posting dengan referensi Instagram (@username, instagram.com/, ig:, dll) yang diambil
4. **Collecting** → Username dan link Instagram diekstrak dan dideduplikasi
5. **Looping** → Setelah semua keyword selesai, keyword diacak dan pencarian dimulai lagi (siklus baru)
6. **Stop** → Tekan `Ctrl+C` kapan saja untuk menghentikan pencarian
7. **Export** → Ekspor hasil ke CSV/Excel melalui menu

### Live Dashboard

Selama pencarian, dashboard real-time menampilkan:
- Jumlah siklus, keyword diproses, posting diperiksa
- **Instagram ditemukan** (counter utama)
- **IG per menit** (kecepatan pencarian)
- Waktu berjalan dan error count
- 5 hasil terbaru

---

## 📁 Struktur Proyek

```
ThreadScout/
│
├── main.py              # Entry point dan menu utama
├── config.py            # Konfigurasi dan pengaturan kecepatan
├── search.py            # Mesin pencari unlimited (10 tab paralel)
├── extractor.py         # Ekstraksi username + link Instagram
├── exporter.py          # Export CSV dan Excel
├── filters.py           # Filter regex untuk posting
├── ui.py                # Komponen UI terminal (Rich)
├── utils.py             # Utilitas umum
│
├── output/              # Hasil ekspor
│   ├── result.csv
│   └── result.xlsx
│
├── logs/                # Log harian
├── config/
│   └── keywords.json    # 60+ keyword default
│
├── requirements.txt
└── README.md
```

---

## 📖 Menu

| No | Menu | Fungsi |
|----|------|--------|
| 1 | 🔍 Start Search | Pencarian unlimited (berjalan hingga Ctrl+C) |
| 2 | 📝 Edit Keywords | Kelola keyword (tambah/hapus/reset) |
| 3 | 📊 View Results | Lihat tabel hasil (hanya yang punya IG) |
| 4 | 📄 Export CSV | Ekspor ke `output/result.csv` |
| 5 | 📗 Export Excel | Ekspor ke `output/result.xlsx` |
| 6 | 📈 Statistics | Dashboard statistik |
| 7 | ⚙️ Settings | Pengaturan aplikasi |
| 0 | 🚪 Exit | Keluar |

---

## 📤 Format Output

Setiap hasil **pasti memiliki username Instagram atau link Instagram** (tidak ada "Not Found").

| Kolom | Contoh |
|-------|--------|
| Threads | @user123 |
| Instagram | @rifki.xyz |
| Instagram Link | https://www.instagram.com/rifki.xyz |
| Keyword | moots |
| Post URL | https://www.threads.net/@user123/post/... |
| Post Content | hey drop ig kalian, moots yuk... |
| Date Scraped | 2026-07-18 12:30:00 |

### Contoh Tabel Output

| Threads | Instagram | Instagram Link | Keyword |
|---------|-----------|----------------|---------|
| @user1 | @rifki.xyz | https://www.instagram.com/rifki.xyz | moots |
| @user2 | @design.id | https://www.instagram.com/design.id | drop ig |
| @user3 | @uiuxdaily | https://www.instagram.com/uiuxdaily | mutual |

---

## 🔧 Troubleshooting

### Browser gagal diluncurkan
```bash
playwright install chromium
```

### Timeout saat pencarian
- Periksa koneksi internet
- Coba: `python main.py --scroll 2`
- Debug: `python main.py --no-headless`

### CAPTCHA / Login wall
- Tunggu beberapa menit, coba lagi
- Keyword yang terkena CAPTCHA akan di-skip otomatis

### File export gagal
- Tutup file CSV/Excel yang sedang dibuka
- Periksa izin tulis folder `output/`

---

## ⚖️ Lisensi

MIT License — Lihat file [LICENSE](LICENSE) untuk detail.

---

## ⚠️ Disclaimer

ThreadScout dirancang untuk **tujuan riset dan analisis komunitas**. Pengguna bertanggung jawab untuk mematuhi ketentuan layanan platform. Aplikasi ini hanya mengumpulkan data yang tersedia secara publik dan tidak melakukan tindakan otomatis seperti follow, DM, atau interaksi akun.
