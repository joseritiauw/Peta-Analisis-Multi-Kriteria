# PRD — Redesain UI Dashboard Indeks Risiko Banjir Surabaya

## 1. Konteks
Aplikasi Streamlit untuk visualisasi indeks risiko banjir per kecamatan di Kota Surabaya (peta interaktif + panel analitik per lokasi). UI saat ini menggunakan palet warna default Tailwind (biru/merah/kuning/hijau saturasi tinggi), efek glassmorphism, dan campuran tema terang/gelap yang tidak konsisten — kesannya generik seperti template dashboard AI-generated, bukan alat kerja analisis kebencanaan yang presisi dan tepercaya.

## 2. Tujuan
Rombak seluruh sistem visual (warna, tipografi, layout, komponen) menjadi lebih **natural, minim warna, dan terasa profesional/institusional** — terinspirasi dari peta hazard/topografi asli (BPBD, BMKG, geological survey) yang memakai gradasi warna bumi (hypsometric tinting), bukan skema traffic-light neon.

Arah yang sudah disepakati: **tema terang seperti kertas peta** (krem, teks gelap) — bukan dark mode.

## 3. Non-goals
- Tidak mengubah logika/fungsi aplikasi (perhitungan skor, pembacaan raster, struktur data).
- Tidak mengubah struktur komponen Streamlit (tabs, dialog, folium map) — hanya styling dan sebagian teks label.

## 4. Design Tokens

### Warna
| Token | Hex | Penggunaan |
|---|---|---|
| `--paper` | `#F4F1EA` | Latar utama aplikasi |
| `--paper-raised` | `#FBF9F4` | Kartu, panel, dialog |
| `--ink` | `#2B2A28` | Teks utama |
| `--ink-muted` | `#8A8375` | Teks sekunder/label |
| `--line` | `#DDD6C7` | Border, divider, grid |
| `--low` | `#7A8B6F` | Risiko rendah (sage) |
| `--med` | `#C08A3E` | Risiko sedang (ochre) |
| `--high` | `#A13D2B` | Risiko tinggi (rust) |
| `--accent` | `#3E6E75` | Aksen interaktif/air (teal pudar), dipakai terbatas — bukan warna dominan |
| `--accent-soft` | `rgba(62,110,117,0.10)` | Latar ikon/elemen aksen |

**Aturan penting**: jangan pakai warna neon/saturasi tinggi (mis. `#3B82F6`, `#EF4444`, `#F59E0B`, `#22C55E`) di mana pun, termasuk di **colormap raster peta** (overlay risiko di peta harus pakai gradasi 5-kelas dari `--low` → `--med` → `--high`, bukan skema RdYlGn default GIS). Warna hanya boleh membawa makna (level risiko); elemen dekoratif (ikon KPI, ikon rekomendasi, dll.) harus pakai satu warna aksen yang sama, bukan warna berbeda-beda per kartu.

### Tipografi
- **Display/judul**: `Spectral` (serif) — dipakai di judul header, judul dialog, nama kecamatan, judul kartu rekomendasi. Kesan laporan resmi/ilmiah.
- **Body/UI**: `IBM Plex Sans` — teks umum, label, tab, paragraf.
- **Data/angka**: `IBM Plex Mono` — skor, koordinat, persentase, badge, label KPI (uppercase, letter-spacing lebar). Kesan presisi teknikal.
- Hapus semua referensi font `Inter`.

### Layout & bentuk
- Border-radius kecil: 4–8px (bukan 12–24px).
- Border hairline 1px `--line`, bukan box-shadow tebal.
- Hilangkan semua `backdrop-filter: blur()` dan efek glassmorphism.
- Satu tema konsisten di seluruh permukaan: header, dialog popup, legend peta, panel ranking mengambang, footer — semua pakai `--paper` / `--paper-raised`, tidak ada lagi dark panel yang tabrakan dengan tema terang.
- Gradient linear dua-warna pada progress bar diganti warna flat sesuai level (`--low`/`--med`/`--high`).

## 5. Spesifikasi per komponen

1. **Header atas**: judul "Indeks Risiko Banjir" (serif) + subjudul kecil "Kota Surabaya — Peta Analisis Multi-Kriteria" (mono, uppercase, muted). Background `--paper-raised`, border-bottom `--line`, tanpa blur/shadow tebal.
2. **Peta (folium)**: raster overlay pakai colormap 5-kelas natural (`--low` → `--med` → `--high`), bukan skema hijau-kuning-oranye-merah saturasi tinggi. Titik validasi/marker pakai `--accent`. Garis batas wilayah pakai `--ink`.
3. **Legend peta**: kotak `--paper-raised` dengan border `--line`, judul mono uppercase, 3 baris warna (Rendah/Sedang/Tinggi) sesuai token.
4. **Panel ranking mengambang (kanan)**: tombol toggle netral (`--paper-raised` + border, bukan tombol oranye solid). Kartu ringkasan & daftar kecamatan pakai `--paper-raised`/`--line`, tanpa glass blur.
5. **Kartu kecamatan (district-card)**: border tipis, radius kecil, badge risiko dengan warna token, mini progress bar warna flat sesuai level.
6. **Dialog "Dashboard Analytics" saat klik peta**: background `--paper` (bukan dark rgba), radius kecil, tanpa blur. Judul kecamatan pakai serif.
7. **KPI cards (Populasi, Elevasi, Skor Risiko, Kategori)**: 3 dari 4 ikon pakai satu warna aksen yang sama (`--accent` di atas `--accent-soft`) — jangan biru/ungu/pink berbeda-beda. Hanya kartu "Kategori" yang boleh mengikuti warna level risiko, karena itu satu-satunya yang membawa makna warna.
8. **Tab Ringkasan**: gauge chart Plotly direstyle ke tema terang (bar teal, steps warna pudar sesuai level, font ink/mono). Kartu rekomendasi kebijakan pakai border-left aksen, ikon dengan satu warna aksen konsisten.
9. **Tab Parameter**: progress bar per parameter pakai warna flat sesuai level (bukan gradient dua-warna).
10. **Tab Visualisasi**: radar chart direstyle ke tema terang (grid `--line`, teks `--ink`/`--ink-muted`, fill `--accent` transparan). Panel kontribusi risiko (Hazard/Exposure/Vulnerability) pakai teks ink, angka mono, tanpa warna merah/kuning/hijau berbeda per baris — cukup satu warna ink untuk semua angka supaya tidak ramai.
11. **Footer status bar**: `--paper-raised`, teks mono kecil, warna `--ink-muted`/`--ink`.
12. **Bahasa**: label UI, badge, tab, dan teks status disarankan pakai Bahasa Indonesia agar konsisten (mis. "Risiko Tinggi/Sedang/Rendah", "Ringkasan & Peringkat Risiko", nama tab "Ringkasan/Parameter/Visualisasi/Riwayat").

## 6. Kriteria selesai (acceptance criteria)
- [ ] Tidak ada lagi warna neon Tailwind (`#3B82F6`, `#EF4444`, `#F59E0B`, `#22C55E`, dll.) di CSS, komponen HTML inline, maupun konfigurasi chart Plotly.
- [ ] Tidak ada `backdrop-filter: blur` atau tema gelap tersisa di komponen manapun.
- [ ] Semua permukaan (header, dialog, legend, panel, footer) memakai token warna yang sama dan terasa satu sistem.
- [ ] Font `Inter` sudah tidak dipakai; diganti Spectral + IBM Plex Sans + IBM Plex Mono sesuai peruntukan di atas.
- [ ] Colormap raster peta memakai gradasi natural 5-kelas, bukan skema RdYlGn default.
- [ ] Ikon dekoratif (KPI, rekomendasi) memakai satu warna aksen konsisten, warna hanya dipakai untuk membawa makna risiko.
- [ ] Border-radius dan shadow diperkecil/ditipiskan di seluruh komponen (tidak ada lagi radius 12–24px atau shadow tebal bergaya "card floating" konsumer).
