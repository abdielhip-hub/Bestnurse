import json
import os
import shutil
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_DATABASE = os.path.join(BASE_DIR, "data_antrean.json")

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
    def _inisialisasi_data_baru(self):
        """Membuat struktur data kosong untuk hari ini"""
        self.antrean_per_bidang = {b: [] for b in self.daftar_bidang}
        self.counter_nomor_urut = {b: 0 for b in self.daftar_bidang}

    def _cadangkan_file(self, akhiran: str):
        """Menyalin file database lama agar tidak hilang tertimpa"""
        tujuan = os.path.join(BASE_DIR, f"data_antrean_{akhiran}.json")
        try:
            shutil.copy(FILE_DATABASE, tujuan)
            return tujuan
        except OSError:
            return None

    def muat_data(self):
        """Membaca data dari file JSON; nomor urut di-reset setiap hari"""
        self._inisialisasi_data_baru()

        if not os.path.exists(FILE_DATABASE):
            return

        try:
            with open(FILE_DATABASE, "r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError("Format data tidak valid")
        except (json.JSONDecodeError, ValueError, OSError):
            cadangan = self._cadangkan_file("rusak_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            print("⚠️  File data rusak, memulai data baru.")
            if cadangan:
                print(f"    File lama disimpan di: {cadangan}")
            return

        # Ganti hari -> arsipkan data kemarin, mulai nomor urut dari 1 lagi
        tanggal_file = data.get("tanggal", self.tanggal)
        if tanggal_file != self.tanggal:
            self._cadangkan_file(str(tanggal_file))
            return

        antrean = data.get("antrean", {})
        counter = data.get("counter", {})
        for bidang in self.daftar_bidang:
            pasien_list = antrean.get(bidang, [])
            for p in pasien_list:
                p.setdefault("status", STATUS_MENUNGGU)  # kompatibel dengan data versi lama
            self.antrean_per_bidang[bidang] = pasien_list
            try:
                self.counter_nomor_urut[bidang] = int(counter.get(bidang, 0))
            except (TypeError, ValueError):
                self.counter_nomor_urut[bidang] = len(pasien_list)

    def simpan_data(self):
        """Menyimpan data secara atomik (tulis ke file sementara lalu ganti)"""
        data = {
            "tanggal": self.tanggal,
            "antrean": self.antrean_per_bidang,
            "counter": self.counter_nomor_urut,
        }
        sementara = FILE_DATABASE + ".tmp"
        try:
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
            sedang["status"] = STATUS_SELESAI  # pasien sebelumnya dianggap selesai

        menunggu = self._pasien_menunggu(bidang)
        if not menunggu:
            self.simpan_data()
            print("📂 Tidak ada pasien lagi yang menunggu.")
            return

        berikutnya = menunggu[0]
        berikutnya["status"] = STATUS_DIPANGGIL
        self.simpan_data()
        print(f"\n📢 Memanggil {self._kode_antrean(bidang, berikutnya['nomor_urut'])} - {berikutnya['nama']}")
        print(f"   Umur: {berikutnya['umur']} tahun | Keluhan: {berikutnya['keluhan']}")

    def _akhiri_pasien(self, bidang: str, status_baru: str):
        sedang = self._pasien_sedang_dipanggil(bidang)
        if not sedang:
            print("❌ Tidak ada pasien yang sedang dipanggil.")
            return
        sedang["status"] = status_baru
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
                print("4. Keluar dari Aplikasi")

                pilihan = input("Pilih menu (1-4): ").strip()

                if pilihan == "1":
                    self.menu_pasien()
                elif pilihan == "2":
                    self.menu_cek_antrean()
                elif pilihan == "3":
                    self.menu_dokter()
                elif pilihan == "4":
                    break
                else:
                    print("❌ Pilihan tidak valid. Silakan masukkan angka 1-4.")
        except (KeyboardInterrupt, EOFError):
            print()

        print("\nTerima kasih. Data antrean tersimpan secara aman.")


if __name__ == "__main__":
    rs = SistemRumahSakit("RS Sehat Sentosa")
    rs.jalankan()
