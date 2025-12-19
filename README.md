# 🚛 Logistics Simulation - Dokumentasi Aplikasi

## Deskripsi Umum
Aplikasi **Logistics Simulation** adalah aplikasi berbasis web yang dibangun menggunakan **Streamlit** untuk mensimulasikan dan memvisualisasikan perbandingan dua skenario pengiriman logistik:
1. **Base Case** - Rute pengiriman standar (Port → Bongkar → Port → Muat → Port)
2. **Triangulasi** - Rute pengiriman yang dioptimasi (Port → Bongkar → Muat → Port)

## Tujuan Aplikasi
- Membandingkan efisiensi jarak tempuh antara skenario base case dan triangulasi
- Menghitung estimasi penghematan biaya (cost saving)
- Memvisualisasikan rute pengiriman secara interaktif pada peta
- Menampilkan simulasi pergerakan truk secara animasi time-series

## Cara Kerja

### 1. Input Data
- Pengguna mengunggah file Excel (`.xlsx`) yang berisi data mapping pengiriman
- File harus memiliki kolom: `DEST_ID`, `CABANG`, `DEST_LAT`, `DEST_LON`, `ORG_LAT`, `ORG_LON`, `STATUS`, dll.
- Data dengan status `MATCHED` akan diproses

### 2. Pemilihan Trip
- Pengguna memilih trip berdasarkan kombinasi `DEST_ID` dan `CABANG`
- Sistem mengambil koordinat lokasi bongkar (destination), muat (origin), dan port

### 3. Perhitungan Rute
- Menggunakan **Valhalla Routing Engine** (localhost:8002) untuk mendapatkan shape rute jalan
- Jika Valhalla tidak tersedia, fallback ke garis lurus antar titik
- Rute di-interpolasi untuk menghasilkan animasi yang smooth

### 4. Visualisasi
- Dua peta interaktif ditampilkan side-by-side menggunakan **Folium**
- **TimestampedGeoJson** digunakan untuk animasi pergerakan truk
- Marker menunjukkan lokasi Port (biru), Bongkar (merah), dan Muat (hijau)

## Komponen Utama

| Fungsi | Deskripsi |
|--------|-----------|
| `haversine()` | Menghitung jarak antara dua koordinat geografis |
| `interpolate_points()` | Menambahkan titik-titik antara untuk animasi smooth |
| `get_route_shape()` | Mengambil geometri rute dari Valhalla API |
| `create_smooth_geojson()` | Membuat GeoJSON untuk animasi timestamped |
| `format_rp()` | Format angka ke format Rupiah Indonesia |

## Dependensi
- `streamlit` - Framework web UI
- `pandas` - Manipulasi data
- `folium` - Visualisasi peta
- `streamlit_folium` - Integrasi Folium dengan Streamlit
- `requests` - HTTP client untuk API Valhalla
- `polyline` - Decode polyline dari Valhalla
- `numpy` - Operasi numerik

## Konfigurasi
- **Valhalla URL**: `http://localhost:8002/route`
- **PORT_LOCATIONS**: Dictionary koordinat pelabuhan di Indonesia
- **Default Speed**: 60 km/jam untuk simulasi

## Output Metrics
- **Jarak Base Case** (km) - Total jarak skenario standar
- **Jarak Triangulasi** (km) - Total jarak skenario optimasi
- **Net Saving** (Rp) - Estimasi penghematan biaya
- **Idle Time** (Jam) - Waktu tunggu/idle