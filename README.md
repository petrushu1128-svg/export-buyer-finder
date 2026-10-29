# Export Buyer Finder — MVP v1.1

Website statis responsif untuk riset wood pellet Asia. Tidak perlu server berbayar.

## Apa yang benar-benar bekerja
- Dashboard dan pencatatan calon buyer, URL bukti, email publik, filter, CSV impor/ekspor (tersimpan di **browser/perangkat yang sama**).
- Pencarian Google/Bing yang dibuka manual.
- Kolektor otomatis berita publik Google News RSS untuk sekitar 30 negara Asia, via GitHub Actions setiap hari sekitar 09.17 WIB (jadwal GitHub bisa terlambat).
- Panel sinyal pasar dari `data/signals.json` dengan filter dan tautan sumber.

**PENTING:** Berita hanya *lead untuk riset*, bukan bukti perusahaan melakukan impor. Tidak ada validasi shipment, pengambilan email otomatis, atau cloud database. Jangan menganggap status `shipment` sebagai verifikasi independen. Berita dapat kosong atau terputus jika RSS membatasi akses.

## Deploy gratis dari Android (GitHub Pages)
1. Buat repository GitHub baru, misalnya `export-buyer-finder`. Jika data buyer bersifat rahasia, jangan unggah CSV ke repository publik.
2. Unggah **isi folder** ini ke root repository (termasuk `.github/workflows/collect.yml` dan `data/signals.json`). Dari Android, GitHub web mendukung upload file, tetapi file tersembunyi `.github` lebih mudah ditambahkan lewat editor web GitHub atau GitHub Codespaces.
3. Settings → Pages → Build and deployment → Deploy from a branch → `main` / `(root)` → Save.
4. Actions → `Collect public wood-pellet news signals` → Run workflow. Jika Actions tidak aktif, aktifkan dari tab Actions.
5. Setelah workflow selesai dan commit `data/signals.json` muncul, buka alamat Pages yang ditampilkan GitHub. Tunggu deployment Pages selesai; klik **Muat ulang sinyal**.
6. Untuk cek hasil otomatis: Actions → workflow → log, dan buka `data/signals.json`. Jadwal GitHub tidak menjamin eksekusi tepat waktu dan bisa dinonaktifkan setelah repo lama tidak aktif.

## Menjalankan lokal
`python -m http.server 8000` dari folder proyek, lalu buka `http://localhost:8000`.
`python collector.py` untuk mengambil sinyal secara manual (perlu internet). Membuka `index.html` sebagai `file://` tidak bisa mengambil JSON melalui `fetch` pada banyak browser.

## Keamanan dan batasan
- **Tidak ada scraping akun/login, bypass proteksi, maupun email harvesting**.
- Semua kontak yang dimasukkan harus berasal dari sumber publik yang legal; konfirmasi hak penggunaan data sebelum outreach.
- Penyimpanan `localStorage` bisa hilang bila browser dihapus. Ekspor CSV berkala. Tidak sinkron antar perangkat.
- URL sumber berita Google News mungkin mengarah melalui redirect.
- Hindari mengunggah kontak/email atau CSV buyer ke repo publik.
- API data impor berbayar diperlukan untuk verifikasi shipment otomatis yang sungguhan.
