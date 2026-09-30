# Sistem Antrean Poliklinik

Aplikasi antrean poliklinik rumah sakit berbasis terminal, ditulis dengan Python murni (tanpa library tambahan). Pasien mendaftar dan mendapat nomor antrean per poli, dokter memanggil pasien satu per satu, dan petugas dapat melihat rekap harian beserta nama pasien yang dilewati.

## Fitur

**Pasien**
- Pendaftaran dengan nama, umur, poli tujuan, dan keluhan
- Nomor antrean per poli (contoh: `U-001`, `G-003`) dan jumlah antrean di depan
- Cek status antrean: nomor yang sedang dipanggil dan posisi antrean

**Dokter** (dengan PIN)
- Melihat daftar pasien yang menunggu beserta keluhannya
- Memanggil pasien berikutnya
- Menandai pasien selesai atau dilewati (tidak hadir)

**Petugas** (dengan PIN yang sama)
- Rekap hari ini dan rekap hari tertentu
- Per poli: total pasien, selesai, dilewati, belum terlayani, rata-rata waktu tunggu
- Daftar nama pasien yang dilewati, lengkap dengan umur, keluhan, jam daftar, dan jam dipanggil

**Lainnya**
- Nomor antrean mulai dari 1 lagi setiap hari
- Data tersimpan otomatis dan tetap ada setelah program ditutup
- Penulisan file atomik, dan file rusak dicadangkan otomatis

## Cara Menjalankan

Kebutuhan: Python 3.8 atau lebih baru.

```bash
python antrean_rs.py
```

Di Windows bisa juga memakai `py antrean_rs.py`.

## Contoh Alur

1. Pilih **1. Daftar sebagai Pasien**, isi data, lalu catat nomor antrean yang muncul.
2. Pilih **3. Masuk sebagai Dokter**, masukkan PIN, pilih poli, lalu **Panggil pasien berikutnya**.
3. Setelah selesai, pilih **Tandai pasien sekarang selesai**. Jika pasien tidak hadir, pilih **Lewati pasien sekarang**.
4. Pilih **4. Laporan & Riwayat (Petugas)** untuk melihat rekap.

## Konfigurasi

| Pengaturan | Default | Keterangan |
|---|---|---|
| PIN dokter dan petugas | `1234` | Ganti lewat environment variable `PIN_DOKTER` |
| Daftar poli | Umum, Gigi, Mata, Anak, THT | Ubah di dictionary `BIDANG_KODE` di `antrean_rs.py` |
| Batas percobaan PIN | 3 kali | Konstanta `MAKS_PERCOBAAN_PIN` |

Contoh mengganti PIN:

```bash
# Linux / macOS
PIN_DOKTER=987654 python antrean_rs.py

# Windows (PowerShell)
$env:PIN_DOKTER="987654"; python antrean_rs.py
```

Untuk menambah poli, tambahkan satu baris di `BIDANG_KODE` dengan kode huruf yang unik:

```python
BIDANG_KODE = {
    "Dokter Umum": "U",
    "Dokter Kulit": "K",  # poli baru
}
```

## Penyimpanan Data

Semua data disimpan dalam satu file: `data/antrean.json`, yang berisi seluruh hari. Struktur singkatnya:

```json
{
    "hari": {
        "2026-09-29": {
            "antrean": {
                "Dokter Mata": [
                    {
                        "nomor_urut": 1,
                        "nama": "Budi",
                        "umur": 30,
                        "keluhan": "Mata perih",
                        "status": "selesai",
                        "waktu_daftar": "21:08:08",
                        "waktu_dipanggil": "21:15:00",
                        "waktu_selesai": "21:25:00"
                    }
                ]
            },
            "counter": { "Dokter Mata": 1 }
        }
    }
}
```

Status pasien: `menunggu`, `dipanggil`, `selesai`, `dilewati`.

Catatan:
- Rekap hari lain dilihat lewat menu, jadi file JSON tidak perlu dibuka manual.
- Jika `data/antrean.json` rusak, program memulai data baru dan menyimpan salinan file lama sebagai `data/antrean_rusak_<waktu>.json`.
- Jika ada file lama `data_antrean*.json` (versi sebelumnya) di folder program, isinya dipindahkan otomatis sekali saja. File lama itu boleh dihapus setelahnya.

## Privasi dan Keamanan

File data berisi nama, umur, dan keluhan pasien. Beberapa hal yang perlu diperhatikan:

- Jangan menaruh folder `data/` di repositori publik. Jika memakai Git, tambahkan `data/` ke `.gitignore`.
- PIN default `1234` sebaiknya segera diganti.
- PIN ini hanya pengaman sederhana untuk penggunaan terminal, bukan sistem autentikasi penuh. Data di file JSON tidak dienkripsi.

## Struktur Proyek

```
.
├── antrean_rs.py    # seluruh aplikasi
├── README.md
└── data/
    └── antrean.json # dibuat otomatis saat ada pasien mendaftar
```

## Batasan Saat Ini

- Dirancang untuk satu komputer dan satu pengguna pada satu waktu. Menjalankan dua instance sekaligus dapat menyebabkan data saling menimpa.
- Belum ada fitur pembatalan antrean oleh pasien.
- Waktu dicatat sebagai jam saja (`HH:MM:SS`), sehingga waktu tunggu yang melewati tengah malam tidak dihitung.

## Ide Pengembangan

- Batalkan antrean oleh pasien
- Prioritas pasien (lansia, ibu hamil, darurat)
- Ekspor rekap ke CSV
- Ganti JSON dengan SQLite
- Antarmuka web (Flask atau FastAPI)
