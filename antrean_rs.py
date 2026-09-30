import json
import os
import re
import shutil
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE_DATABASE = os.path.join(DATA_DIR, "antrean.json")

PIN_DOKTER = os.environ.get("PIN_DOKTER", "1234")
MAKS_PERCOBAAN_PIN = 3

BIDANG_KODE = {
    "Dokter Umum": "U",
    "Dokter Gigi": "G",
    "Dokter Mata": "M",
    "Dokter Anak": "A",
    "Dokter THT": "T",
}

STATUS_MENUNGGU = "menunggu"
STATUS_DIPANGGIL = "dipanggil"
STATUS_SELESAI = "selesai"
STATUS_DILEWATI = "dilewati"


class SistemRumahSakit:
    def __init__(self, nama_rs: str):
        self.nama_rs = nama_rs
        self.daftar_bidang = list(BIDANG_KODE)
        self.tanggal = date.today().isoformat()
        self.muat_data()

    # ------------------------------------------------------------------
    # Penyimpanan data 
    # ------------------------------------------------------------------
    def _hari_kosong(self):
        return {
            "antrean": {b: [] for b in self.daftar_bidang},
            "counter": {b: 0 for b in self.daftar_bidang},
        }

    def _normalisasi_hari(self, data_hari):
        """Melengkapi struktur data satu hari agar semua bidang tersedia"""
        hari = self._hari_kosong()
        if not isinstance(data_hari, dict):
            return hari
        antrean = data_hari.get("antrean", {})
        counter = data_hari.get("counter", {})
        for bidang in self.daftar_bidang:
            pasien_list = antrean.get(bidang, [])
            if not isinstance(pasien_list, list):
                pasien_list = []
            for p in pasien_list:
                p.setdefault("status", STATUS_MENUNGGU)
            hari["antrean"][bidang] = pasien_list
            try:
                hari["counter"][bidang] = max(int(counter.get(bidang, 0)), len(pasien_list))
            except (TypeError, ValueError):
                hari["counter"][bidang] = len(pasien_list)
        return hari

    @staticmethod
    def _baca_json(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError):
            return None

    def _migrasi_file_lama(self) -> int:
        """Memindahkan data dari versi lama (data_antrean*.json) satu kali saja"""
        pola = re.compile(r"^data_antrean(?:_(\d{4}-\d{2}-\d{2}))?\.json$")
        jumlah = 0
        for nama in sorted(os.listdir(BASE_DIR)):
            cocok = pola.match(nama)
            if not cocok:
                continue
            data = self._baca_json(os.path.join(BASE_DIR, nama))
            if not data or "antrean" not in data:
                continue
            tanggal = str(data.get("tanggal") or cocok.group(1) or self.tanggal)
            self.semua_hari[tanggal] = self._normalisasi_hari(data)
            jumlah += 1
        return jumlah

    def muat_data(self):
        """Membaca semua data dari satu file JSON"""
        self.semua_hari = {}
        hasil_migrasi = 0

        if os.path.exists(FILE_DATABASE):
            data = self._baca_json(FILE_DATABASE)
            if data is None:
                os.makedirs(DATA_DIR, exist_ok=True)
                cadangan = os.path.join(
                    DATA_DIR, "antrean_rusak_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
                try:
                    shutil.copy(FILE_DATABASE, cadangan)
                    print(f"⚠️  File data rusak, memulai data baru. File lama disimpan di: {cadangan}")
                except OSError:
                    print("⚠️  File data rusak, memulai data baru.")
            else:
                for tanggal, data_hari in data.get("hari", {}).items():
                    self.semua_hari[tanggal] = self._normalisasi_hari(data_hari)
        else:
            hasil_migrasi = self._migrasi_file_lama()

        if self.tanggal not in self.semua_hari:
            self.semua_hari[self.tanggal] = self._hari_kosong()
        hari_ini = self.semua_hari[self.tanggal]
        self.antrean_per_bidang = hari_ini["antrean"]
        self.counter_nomor_urut = hari_ini["counter"]

        if hasil_migrasi:
            self.simpan_data()
            print(f"ℹ️  Data lama ({hasil_migrasi} hari) dipindahkan ke {FILE_DATABASE}.")
            print("    File data_antrean*.json yang lama boleh dihapus.")

    def simpan_data(self):
        """Menyimpan data secara atomik (tulis ke file sementara lalu ganti)"""
        data = {"hari": {t: d for t, d in self.semua_hari.items() if any(d["antrean"].values())}}
        sementara = FILE_DATABASE + ".tmp"
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(sementara, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            os.replace(sementara, FILE_DATABASE)
        except OSError as e:
            print(f"❌ Gagal menyimpan data: {e}")

    # ------------------------------------------------------------------
    # Helper input
    # ------------------------------------------------------------------
    @staticmethod
    def _input_angka(prompt: str, minimal: int, maksimal: int):
        try:
            nilai = int(input(prompt).strip())
        except ValueError:
            print("❌ Input harus berupa angka.")
            return None
        if not (minimal <= nilai <= maksimal):
            print(f"❌ Angka harus antara {minimal} dan {maksimal}.")
            return None
        return nilai

    def _pilih_bidang(self):
        """Menu memilih bidang dokter"""
        print("\n--- PILIH BIDANG SPESIALISASI ---")
        for idx, bidang in enumerate(self.daftar_bidang, start=1):
            print(f"{idx}. {bidang}")

        pilihan = self._input_angka("Pilih bidang (angka): ", 1, len(self.daftar_bidang))
        return self.daftar_bidang[pilihan - 1] if pilihan else None

    @staticmethod
    def _kode_antrean(bidang: str, nomor: int) -> str:
        return f"{BIDANG_KODE[bidang]}-{nomor:03d}"

    def _cari_pasien(self, bidang: str, nomor: int):
        for p in self.antrean_per_bidang[bidang]:
            if p["nomor_urut"] == nomor:
                return p
        return None

    def _pasien_sedang_dipanggil(self, bidang: str):
        for p in self.antrean_per_bidang[bidang]:
            if p["status"] == STATUS_DIPANGGIL:
                return p
        return None

    def _pasien_menunggu(self, bidang: str):
        return [p for p in self.antrean_per_bidang[bidang] if p["status"] == STATUS_MENUNGGU]

    # ------------------------------------------------------------------
    # Menu pasien
    # ------------------------------------------------------------------
    def menu_pasien(self):
        """Pendaftaran pasien baru"""
        print("\n=== PENDAFTARAN PASIEN ===")
        nama = input("Masukkan Nama Anda: ").strip()
        if not nama:
            print("❌ Nama tidak boleh kosong!")
            return

        umur = self._input_angka("Masukkan Umur Anda: ", 0, 120)
        if umur is None:
            return

        bidang = self._pilih_bidang()
        if not bidang:
            return

        keluhan = input("Masukkan Keluhan Singkat Anda: ").strip()
        if not keluhan:
            print("❌ Keluhan tidak boleh kosong!")
            return

        self.counter_nomor_urut[bidang] += 1
        no_urut = self.counter_nomor_urut[bidang]
        menunggu_didepan = len(self._pasien_menunggu(bidang))

        self.antrean_per_bidang[bidang].append({
            "nomor_urut": no_urut,
            "nama": nama,
            "umur": umur,
            "keluhan": keluhan,
            "status": STATUS_MENUNGGU,
            "waktu_daftar": datetime.now().strftime("%H:%M:%S"),
        })
        self.simpan_data()

        print("\n" + "=" * 40)
        print("      BUKTI PENDAFTARAN PASIEN")
        print("=" * 40)
        print(f"Tanggal     : {self.tanggal}")
        print(f"Nama Pasien : {nama}")
        print(f"Tujuan Poli : {bidang}")
        print(f"NOMOR URUT  : {self._kode_antrean(bidang, no_urut)}")
        print(f"Antrean di depan Anda: {menunggu_didepan} orang")
        print("=" * 40)
        print(" Silakan menunggu di ruang tunggu.")
        print("=" * 40)

    def menu_cek_antrean(self):
        """Pasien mengecek posisi antreannya"""
        print("\n=== CEK STATUS ANTREAN ===")
        bidang = self._pilih_bidang()
        if not bidang:
            return

        maks = self.counter_nomor_urut[bidang]
        if maks == 0:
            print(f"📂 Belum ada antrean di {bidang} hari ini.")
            return

        nomor = self._input_angka(f"Masukkan nomor urut Anda (1-{maks}): ", 1, maks)
        if nomor is None:
            return

        pasien = self._cari_pasien(bidang, nomor)
        if not pasien:
            print("❌ Nomor urut tidak ditemukan.")
            return

        sedang = self._pasien_sedang_dipanggil(bidang)
        print(f"\nNomor {self._kode_antrean(bidang, nomor)} a.n. {pasien['nama']}")
        print(f"Status  : {pasien['status'].upper()}")
        if sedang:
            print(f"Sedang dipanggil: {self._kode_antrean(bidang, sedang['nomor_urut'])}")
        if pasien["status"] == STATUS_MENUNGGU:
            didepan = sum(1 for p in self._pasien_menunggu(bidang) if p["nomor_urut"] < nomor)
            print(f"Antrean di depan Anda: {didepan} orang")

    # ------------------------------------------------------------------
    # Menu dokter
    # ------------------------------------------------------------------
    def _verifikasi_pin(self) -> bool:
        for sisa in range(MAKS_PERCOBAAN_PIN, 0, -1):
            if input("Masukkan PIN dokter: ").strip() == PIN_DOKTER:
                return True
            print(f"❌ PIN salah. Sisa percobaan: {sisa - 1}")
        return False

    def _tampilkan_daftar(self, bidang: str):
        menunggu = self._pasien_menunggu(bidang)
        sedang = self._pasien_sedang_dipanggil(bidang)
        selesai = sum(1 for p in self.antrean_per_bidang[bidang] if p["status"] == STATUS_SELESAI)

        print("\n" + "=" * 45)
        print(f" PANEL DOKTER - POLI {bidang.upper()}")
        print("=" * 45)
        print(f"Menunggu: {len(menunggu)} | Selesai: {selesai}")

        if sedang:
            print(f"\n▶ SEDANG DIPERIKSA: {self._kode_antrean(bidang, sedang['nomor_urut'])} - {sedang['nama']}")
            print(f"  Keluhan: {sedang['keluhan']}")

        if not menunggu:
            print("\n📂 Tidak ada pasien yang menunggu.")
            return

        print()
        for p in menunggu:
            print("-----------------------------------")
            print(f"No. Urut : {self._kode_antrean(bidang, p['nomor_urut'])}")
            print(f"Nama     : {p['nama']}")
            print(f"Umur     : {p['umur']} tahun")
            print(f"Keluhan  : {p['keluhan']}")
        print("-----------------------------------")

    def _panggil_berikutnya(self, bidang: str):
        sedang = self._pasien_sedang_dipanggil(bidang)
        if sedang:
            sedang["status"] = STATUS_SELESAI
            sedang["waktu_selesai"] = self._sekarang()

        menunggu = self._pasien_menunggu(bidang)
        if not menunggu:
            self.simpan_data()
            print("📂 Tidak ada pasien lagi yang menunggu.")
            return

        berikutnya = menunggu[0]
        berikutnya["status"] = STATUS_DIPANGGIL
        berikutnya["waktu_dipanggil"] = self._sekarang()
        self.simpan_data()
        print(f"\n📢 Memanggil {self._kode_antrean(bidang, berikutnya['nomor_urut'])} - {berikutnya['nama']}")
        print(f"   Umur: {berikutnya['umur']} tahun | Keluhan: {berikutnya['keluhan']}")

    def _akhiri_pasien(self, bidang: str, status_baru: str):
        sedang = self._pasien_sedang_dipanggil(bidang)
        if not sedang:
            print("❌ Tidak ada pasien yang sedang dipanggil.")
            return
        sedang["status"] = status_baru
        sedang["waktu_selesai"] = self._sekarang()
        self.simpan_data()
        print(f"✅ {self._kode_antrean(bidang, sedang['nomor_urut'])} ditandai {status_baru}.")

    def menu_dokter(self):
        """Panel khusus dokter"""
        print("\n=== LOGIN DOKTER ===")
        if not self._verifikasi_pin():
            print("🔒 Akses ditolak.")
            return

        bidang = self._pilih_bidang()
        if not bidang:
            return

        while True:
            self._tampilkan_daftar(bidang)
            print("\n1. Panggil pasien berikutnya")
            print("2. Tandai pasien sekarang selesai")
            print("3. Lewati pasien sekarang (tidak hadir)")
            print("4. Kembali ke menu utama")
            pilihan = input("Pilih (1-4): ").strip()

            if pilihan == "1":
                self._panggil_berikutnya(bidang)
            elif pilihan == "2":
                self._akhiri_pasien(bidang, STATUS_SELESAI)
            elif pilihan == "3":
                self._akhiri_pasien(bidang, STATUS_DILEWATI)
            elif pilihan == "4":
                break
            else:
                print("❌ Pilihan tidak valid. Silakan masukkan angka 1-4.")

    # ------------------------------------------------------------------
    # Laporan & riwayat
    # ------------------------------------------------------------------
    @staticmethod
    def _sekarang() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def _selisih_menit(awal, akhir):
        """Selisih dua jam (HH:MM:SS) dalam menit; None jika data tidak lengkap"""
        try:
            fmt = "%H:%M:%S"
            selisih = (datetime.strptime(akhir, fmt) - datetime.strptime(awal, fmt)).total_seconds() / 60
        except (TypeError, ValueError):
            return None
        return selisih if selisih >= 0 else None

    def _cetak_laporan(self, tanggal: str, antrean: dict):
        """Mencetak ringkasan per poli + daftar nama pasien yang dilewati"""
        print("\n" + "=" * 60)
        print(f" LAPORAN ANTREAN - {tanggal}")
        print("=" * 60)

        total = {STATUS_SELESAI: 0, STATUS_DILEWATI: 0, "belum": 0, "semua": 0}
        semua_dilewati = []

        for bidang in self.daftar_bidang:
            pasien_list = antrean.get(bidang, [])
            if not pasien_list:
                continue

            selesai = [p for p in pasien_list if p.get("status") == STATUS_SELESAI]
            dilewati = [p for p in pasien_list if p.get("status") == STATUS_DILEWATI]
            belum = [p for p in pasien_list
                     if p.get("status") in (STATUS_MENUNGGU, STATUS_DIPANGGIL)]

            tunggu = [m for m in (self._selisih_menit(p.get("waktu_daftar"), p.get("waktu_dipanggil"))
                                  for p in pasien_list) if m is not None]
            rata2 = f"{sum(tunggu) / len(tunggu):.1f} menit" if tunggu else "-"

            print(f"\n[{bidang}]")
            print(f"  Total pasien       : {len(pasien_list)}")
            print(f"  Selesai            : {len(selesai)}")
            print(f"  Dilewati           : {len(dilewati)}")
            print(f"  Belum terlayani    : {len(belum)}")
            print(f"  Rata-rata tunggu   : {rata2}")

            if dilewati:
                print("  Pasien yang dilewati (tidak hadir):")
                for p in dilewati:
                    kode = self._kode_antrean(bidang, p["nomor_urut"])
                    print(f"    - {kode}  {p['nama']} ({p['umur']} th) | Keluhan: {p['keluhan']}")
                    print(f"      Daftar: {p.get('waktu_daftar', '-')} | Dipanggil: {p.get('waktu_dipanggil', '-')}")
                    semua_dilewati.append((bidang, p))

            total["semua"] += len(pasien_list)
            total[STATUS_SELESAI] += len(selesai)
            total[STATUS_DILEWATI] += len(dilewati)
            total["belum"] += len(belum)

        if total["semua"] == 0:
            print("\n📂 Tidak ada data pasien pada tanggal ini.")
            return

        print("\n" + "-" * 60)
        print(f" TOTAL SEMUA POLI: {total['semua']} pasien | Selesai: {total[STATUS_SELESAI]} | "
              f"Dilewati: {total[STATUS_DILEWATI]} | Belum terlayani: {total['belum']}")

        if semua_dilewati:
            print("\n Ringkasan nama pasien yang dilewati:")
            for bidang, p in semua_dilewati:
                print(f"   {self._kode_antrean(bidang, p['nomor_urut'])} - {p['nama']} ({bidang})")
        print("=" * 60)

    def _tanggal_tersedia(self):
        """Tanggal yang punya data pasien, terbaru lebih dulu"""
        return sorted(
            (t for t, d in self.semua_hari.items() if any(d["antrean"].values())),
            reverse=True,
        )

    def _menu_rekap_tanggal(self):
        tanggal_list = self._tanggal_tersedia()
        if not tanggal_list:
            print("📂 Belum ada data pasien yang tercatat.")
            return

        print("\n--- PILIH TANGGAL REKAP ---")
        for idx, tgl in enumerate(tanggal_list, start=1):
            total = sum(len(v) for v in self.semua_hari[tgl]["antrean"].values())
            label = " (hari ini)" if tgl == self.tanggal else ""
            print(f"{idx}. {tgl}{label} - {total} pasien")

        pilihan = self._input_angka("Pilih tanggal (angka): ", 1, len(tanggal_list))
        if pilihan is None:
            return
        tanggal = tanggal_list[pilihan - 1]
        self._cetak_laporan(tanggal, self.semua_hari[tanggal]["antrean"])

    def menu_laporan(self):
        """Laporan harian & riwayat (khusus petugas, butuh PIN)"""
        print("\n=== REKAP & RIWAYAT ===")
        if not self._verifikasi_pin():
            print("🔒 Akses ditolak.")
            return

        while True:
            print("\n1. Rekap hari ini")
            print("2. Rekap hari tertentu")
            print("3. Kembali ke menu utama")
            pilihan = input("Pilih (1-3): ").strip()

            if pilihan == "1":
                self._cetak_laporan(self.tanggal, self.antrean_per_bidang)
            elif pilihan == "2":
                self._menu_rekap_tanggal()
            elif pilihan == "3":
                break
            else:
                print("❌ Pilihan tidak valid. Silakan masukkan angka 1-3.")

    # ------------------------------------------------------------------
    # Menu utama
    # ------------------------------------------------------------------
    def jalankan(self):
        """Menu Utama"""
        try:
            while True:
                print("\n" + "=" * 45)
                print(f"   SISTEM ANTREAN POLIKLINIK {self.nama_rs.upper()}")
                print("=" * 45)
                print("1. Daftar sebagai Pasien")
                print("2. Cek Status Antrean")
                print("3. Masuk sebagai Dokter")
                print("4. Laporan & Riwayat (Petugas)")
                print("5. Keluar dari Aplikasi")

                pilihan = input("Pilih menu (1-5): ").strip()

                if pilihan == "1":
                    self.menu_pasien()
                elif pilihan == "2":
                    self.menu_cek_antrean()
                elif pilihan == "3":
                    self.menu_dokter()
                elif pilihan == "4":
                    self.menu_laporan()
                elif pilihan == "5":
                    break
                else:
                    print("❌ Pilihan tidak valid. Silakan masukkan angka 1-5.")
        except (KeyboardInterrupt, EOFError):
            print()

        print("\nTerima kasih. Data antrean tersimpan secara aman.")


if __name__ == "__main__":
    rs = SistemRumahSakit("RS Sehat Sentosa")
    rs.jalankan()
