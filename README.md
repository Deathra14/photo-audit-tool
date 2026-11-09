# Photo Audit Tool

CLI lokal untuk mencocokkan ID pada Excel/CSV dengan koleksi foto. Cocok untuk
tim operasional yang perlu memeriksa ribuan berkas tanpa mengunggah data ke
layanan pihak ketiga.

## Fitur

- membaca CSV langsung dan Excel melalui `openpyxl`;
- mencari foto secara rekursif;
- mencocokkan nama file dengan ID secara case-insensitive;
- menandai ID hilang, foto ganda, ID kosong, dan foto yang tidak tercantum;
- menghasilkan laporan CSV dan ringkasan JSON;
- menghasilkan dashboard laporan HTML yang dapat dibuka di browser;
- mendeteksi file yang benar-benar identik menggunakan SHA-256;
- menyediakan GUI desktop berbasis Tkinter dan CLI untuk otomatisasi;
- tidak mengirim data ke internet.

## Instalasi

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Penggunaan

```powershell
python -m photo_audit audit daftar.xlsx folder_foto --id-column ID --output reports
```

Untuk CSV:

```powershell
python -m photo_audit audit examples/sample_ids.csv folder_foto --id-column ID
```

Secara default, ID foto diambil dari nama file tanpa ekstensi. Opsi
`--match-prefix` membuat `ABC_01.jpg` cocok dengan ID `ABC`.

Tambahkan `--content-hash` untuk mendeteksi foto identik walaupun nama filenya
berbeda. Hasil audit tersedia dalam `audit.csv`, `unlisted_photos.csv`,
`content_duplicates.csv`, `summary.json`, dan `report.html`.

## Antarmuka desktop

```powershell
python -m photo_audit gui
```

GUI memungkinkan pemilihan spreadsheet, folder foto, dan folder laporan tanpa
menulis perintah terminal. Semua pemrosesan tetap dilakukan secara lokal.

## Instalasi sebagai command

```powershell
pip install -e .
photo-audit --help
```

## Privasi

Jangan commit data produksi. Pola `.gitignore` sudah mengecualikan spreadsheet,
CSV (kecuali contoh), dan folder laporan.

Gunakan hanya koleksi yang Anda miliki atau berhak Anda proses. Contoh dalam
repository sepenuhnya sintetis dan tidak memuat data pribadi.

## Tes

```powershell
python -m unittest discover -s tests -v
```

## Lisensi

MIT

