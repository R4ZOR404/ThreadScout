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

**Instagram Mutual Research Tool**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Async-green?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Rich](https://img.shields.io/badge/Rich-Terminal%20UI-purple)](https://rich.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

## 📋 Deskripsi

**ThreadScout** adalah aplikasi terminal modern yang membantu pengguna mengumpulkan informasi dari posting Threads yang dapat diakses secara publik berdasarkan kata kunci tertentu, lalu mengekstrak username atau tautan Instagram yang dicantumkan oleh pembuat posting. Hasilnya disimpan ke format **CSV** dan **Excel** untuk keperluan riset, analisis komunitas, atau pengelolaan data.

> ⚠️ Fokus aplikasi adalah **mengumpulkan dan mengekspor data yang tersedia secara publik**, bukan melakukan tindakan otomatis seperti follow, DM, atau interaksi akun.

---

## ✨ Fitur

- 🔍 **Pencarian keyword** — Otomatis mencari 60+ keyword terkait mutual/follow di Threads
- 📸 **Ekstraksi Instagram** — Mengekstrak @username dan tautan instagram.com dari posting
- 📊 **Dashboard Statistik** — Visualisasi hasil pencarian secara real-time
- 📄 **Export CSV/Excel** — Ekspor hasil dengan format profesional dan styling
- 📝 **Manajemen Keyword** — Tambah, hapus, dan reset keyword melalui menu
- 🎨 **UI Modern** — Tampilan terminal bergaya Instagram dengan gradient colors
- 📋 **Logging** — Log harian otomatis untuk debugging dan audit
- 🛡️ **Error Handling** — Penanganan timeout, CAPTCHA, login wall, dan crash

---

## 🛠️ Instalasi

### Prasyarat

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **pip** (biasanya sudah terinstall bersama Python)
- **Git** (opsional)

### Langkah Instalasi

1. **Clone atau download proyek**:

   ```bash
   git clone https://github.com/yourusername/ThreadScout.git
   cd ThreadScout
   ```

2. **Buat virtual environment** (direkomendasikan):

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:

   ```bash
   playwright install chromium
   ```

---

## 🚀 Cara Menjalankan

### Mode Interaktif (Default)

```bash
python main.py
```

### Opsi CLI

```bash
# Jalankan dengan browser visible (non-headless)
python main.py --no-headless

# Atur jumlah scroll per keyword
python main.py --scroll 10

# Tampilkan bantuan
python main.py --help
```

---

## 📁 Struktur Proyek

```
ThreadScout/
│
├── main.py              # Entry point dan menu utama
├── config.py            # Konfigurasi, konstanta, tema warna
├── search.py            # Mesin pencari Threads (Playwright)
├── extractor.py         # Ekstraksi username/link Instagram
├── exporter.py          # Export CSV dan Excel
├── filters.py           # Filter regex untuk posting
├── ui.py                # Komponen UI terminal (Rich)
├── utils.py             # Utilitas umum
│
├── output/              # Hasil ekspor (CSV, Excel)
│   ├── result.csv
│   └── result.xlsx
│
├── logs/                # Log harian
│   └── 2026-07-17.log
│
├── config/              # Konfigurasi
│   └── keywords.json    # Daftar keyword
│
├── requirements.txt     # Dependencies
└── README.md            # Dokumentasi
```

---

## 📖 Penjelasan Menu

| No | Menu | Fungsi |
|----|------|--------|
| 1 | 🔍 Start Search | Memulai pencarian di Threads berdasarkan keyword |
| 2 | 📝 Edit Keywords | Mengelola daftar kata kunci (tambah/hapus/reset) |
| 3 | 📊 View Results | Menampilkan tabel hasil pencarian terbaru |
| 4 | 📄 Export CSV | Mengekspor hasil ke file `output/result.csv` |
| 5 | 📗 Export Excel | Mengekspor hasil ke file `output/result.xlsx` |
| 6 | 📈 Statistics | Dashboard statistik pencarian |
| 7 | ⚙️ Settings | Pengaturan dan informasi aplikasi |
| 0 | 🚪 Exit | Keluar dari ThreadScout |

---

## 🔑 Cara Menambah Keyword

### Via Menu (Direkomendasikan)

1. Jalankan ThreadScout: `python main.py`
2. Pilih menu **2 — Edit Keywords**
3. Pilih opsi **1 — Tambah keyword**
4. Ketik keyword baru dan tekan Enter

### Via File Langsung

Edit file `config/keywords.json`:

```json
{
  "keywords": [
    "moots",
    "mutual",
    "keyword_baru_anda"
  ]
}
```

---

## 📤 Cara Ekspor Hasil

1. Jalankan pencarian terlebih dahulu (menu 1)
2. Pilih menu **4** untuk CSV atau **5** untuk Excel
3. File akan disimpan di folder `output/`

### Format Kolom

| Kolom | Deskripsi |
|-------|-----------|
| Threads | Username Threads pembuat posting |
| Instagram | Username/link Instagram yang ditemukan |
| Keyword | Kata kunci yang cocok |
| Post URL | Link ke posting Threads |
| Post Content | Isi posting (maks 500 karakter) |
| Date Scraped | Tanggal dan waktu pengambilan data |

---

## 🔧 Troubleshooting

### Browser gagal diluncurkan

```bash
# Reinstall Playwright browsers
playwright install chromium
```

### Timeout saat pencarian

- Periksa koneksi internet
- Coba kurangi jumlah scroll: `python main.py --scroll 3`
- Gunakan mode visible untuk debugging: `python main.py --no-headless`

### CAPTCHA terdeteksi

- Tunggu beberapa menit sebelum mencoba lagi
- Kurangi jumlah keyword yang diproses
- Threads mungkin membatasi akses dari IP Anda

### Login diperlukan

- Beberapa konten Threads mungkin memerlukan login
- ThreadScout hanya mengumpulkan data yang tersedia secara publik
- Posting yang memerlukan login akan dilewati

### File export gagal

- Pastikan file CSV/Excel tidak sedang dibuka di aplikasi lain
- Periksa izin tulis di folder `output/`

### Error "Module not found"

```bash
# Pastikan virtual environment aktif
venv\Scripts\activate    # Windows
source venv/bin/activate # Linux/macOS

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📊 Contoh Output

| Threads | Instagram | Keyword |
|---------|-----------|---------|
| @user1 | @rifki.xyz | moots |
| @user2 | @design.id | IG |
| @user3 | @uiuxdaily | talk |
| @user4 | Not Found | mutual |

---

## 📝 Logging

Log disimpan otomatis di folder `logs/` dengan format nama file berdasarkan tanggal:

```
logs/2026-07-17.log
```

Isi log mencakup:
- Startup dan shutdown aplikasi
- Keyword yang diproses
- Jumlah posting ditemukan
- Error dan warning
- Informasi export
- Runtime dan performa

---

## ⚖️ Lisensi

MIT License

```
MIT License

Copyright (c) 2026 ThreadScout

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## ⚠️ Disclaimer

ThreadScout dirancang untuk **tujuan riset dan analisis komunitas**. Pengguna bertanggung jawab untuk mematuhi ketentuan layanan platform dan peraturan yang berlaku. Aplikasi ini hanya mengumpulkan data yang tersedia secara publik dan tidak melakukan tindakan otomatis seperti follow, DM, atau interaksi akun lainnya.
