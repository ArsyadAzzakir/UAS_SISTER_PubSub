
---

## Informasi Mahasiswa
- **Nama:** Muhammad Arsyad Az Zakir
- **NIM:** 11231051
- **Program Studi:** Informatika
- **Institusi:** Institut Teknologi Kalimantan

 **Tautan Video Demonstrasi (YouTube):** `[MASUKKAN_LINK_YOUTUBE_UNLISTED_DI_SINI]`

---

##  Arsitektur dan Teknologi
Sistem ini menggunakan arsitektur *Publish-Subscribe* asinkron untuk mencapai *decoupling* spasial dan temporal antar layanannya.
* **Aggregator (API & Consumer):** Dibangun menggunakan **Python FastAPI** dan `asyncpg`. Bertugas memvalidasi *event*, mengelola koneksi pangkalan data, dan memastikan persistensi.
* **Publisher (Load Generator):** Skrip Python asinkron yang menyimulasikan transmisi puluhan ribu *event* log sensor, dengan probabilitas injeksi data duplikat sebesar 30% untuk menyimulasikan *network retry*.
* **Storage (Durable Store):** Menggunakan **PostgreSQL 16**. Bertindak sebagai pangkalan data transaksional sekaligus *deduplication store*.
* **Orkestrasi:** **Docker Compose** digunakan untuk membungkus semua layanan dalam *default bridge network* internal.

---

##  Struktur Direktori
```text
 UAS_SISTER
 ┣ aggregator/           # Source code untuk layanan API Aggregator (FastAPI)
 ┃ ┣  Dockerfile          # Instruksi build image Aggregator
 ┃ ┣  main.py             # Logika utama aplikasi dan koneksi database
 ┃ ┗  requirements.txt    # Dependensi Python untuk Aggregator
 ┣  publisher/            # Source code untuk layanan Publisher
 ┃ ┣  Dockerfile          # Instruksi build image Publisher
 ┃ ┣  main.py             # Skrip load generator dan simulasi duplikat
 ┃ ┗  requirements.txt    # Dependensi Python untuk Publisher
 ┣  tests/                # Skenario pengujian otomatis
 ┃ ┗  test_api.py         # 15 Unit & Integration tests (Pytest)
 ┣  dashboard/            # (Opsional) Antarmuka visual observability
 ┃ ┗  index.html          # Halaman Live Monitor
 ┣  docker-compose.yml    # Orkestrasi multi-container dan konfigurasi jaringan
 ┣  k6-test.js            # Skrip uji beban (Load Testing)
 ┗  README.md             # Dokumentasi proyek

```

---

## 💡 Keputusan Desain dan Asumsi (*Design Decisions*)

1. **Idempotent Consumer & Deduplication:** Untuk menanggulangi *at-least-once delivery* (pengiriman berulang), pangkalan data dipasang `UNIQUE CONSTRAINT` pada kombinasi `(topic, event_id)`. Sistem dirancang untuk menolak mutasi ganda secara deterministik.
2. **Transaksi & Kontrol Konkurensi:** Menghindari *pessimistic locking* tingkat aplikasi. Sistem menggunakan *optimistic concurrency control* via instruksi SQL `ON CONFLICT DO NOTHING` dalam batas transaksi `READ COMMITTED`. Hal ini mencegah *race condition* secara atomik saat diakses oleh multi-pekerja.
3. **Isolasi Keamanan Jaringan:** Akses ke porta pangkalan data (`5432`) ditutup rapat dari jaringan host publik. Hanya Aggregator yang dapat berkomunikasi dengan pangkalan data di dalam jaringan internal Compose.
4. **Retry with Backoff:** Karena arsitektur terdistribusi tidak menjamin waktu inisialisasi yang serempak, Aggregator dibekali *exponential backoff* agar dapat pulih secara otomatis saat database belum sepenuhnya menyala.

---

## Panduan Instalasi dan Menjalankan Sistem

### Prasyarat

Pastikan mesin Anda telah terinstal **Docker** dan **Docker Compose**.

### Langkah-langkah (Build & Run)

1. Buka terminal (atau terminal terintegrasi di VS Code) dan arahkan ke dalam direktori repositori ini.
2. Jalankan perintah berikut untuk membangun (*build*) dan menyalakan seluruh layanan di latar belakang:
```bash
docker compose up --build -d

```


3. Tunggu beberapa detik hingga proses inisialisasi selesai.
4. Pastikan semua layanan berjalan dengan mengetik:
```bash
docker compose ps

```


5. Aplikasi utama dapat diakses di: **`http://localhost:8080`**

---

## 🔌 Daftar Endpoint API

### 1. Publikasi Event

* **URL:** `POST /publish`
* **Deskripsi:** Menerima event tunggal.
* **Payload Request:**
```json
{
  "topic": "sensor_suhu",
  "event_id": "evt-12345-abcde",
  "timestamp": "2026-06-19T02:00:00Z",
  "source": "device-01",
  "payload": {"suhu": 32.5}
}

```



### 2. Melihat Data Tersimpan

* **URL:** `GET /events`
* **Parameter Opsional:** `?topic=nama_topik`
* **Deskripsi:** Menampilkan maksimal 100 event terbaru (atau difilter berdasarkan topik) yang berhasil dicatat di pangkalan data tanpa duplikat.

### 3. Pemantauan Metrik (Observability)

* **URL:** `GET /stats`
* **Deskripsi:** Menampilkan metrik keteramatan sistem untuk membuktikan terjadinya deduplication.
* **Contoh Response:**
```json
{
  "received": 20000,
  "unique_processed": 16000,
  "duplicate_dropped": 4000,
  "uptime_seconds": 120,
  "topics": ["sensor_suhu", "sensor_cahaya", "sensor_kelembapan"]
}

```



---

##  Panduan Pengujian (*Testing*)

Proyek ini dilengkapi dengan tiga metode pengujian komprehensif untuk memvalidasi spesifikasi. Buka terminal di direktori proyek untuk menjalankan pengujian berikut:

### 1. Automated Unit & Integration Testing (15 Tests)

Menguji *idempotency*, validasi skema JSON, dan konsistensi endpoint secara terisolasi.

```bash
docker run --rm -v "${PWD}/tests:/app" -w /app python:3.11-slim bash -c "pip install pytest httpx && pytest test_api.py -v"

```

*(Ekspektasi: Terminal akan mencetak status **15 Passed** berwarna hijau).*

### 2. Load Testing & Concurrency (K6)

Menyuntikkan 20.000 data menggunakan 50 *Virtual Users* dengan ~30% duplikasi untuk menguji *throughput* dan *race conditions*.

```bash
docker run --rm -v "${PWD}:/app" -w /app grafana/k6 run k6-test.js

```

*(Ekspektasi: Tidak ada error HTTP 500. Buka `http://localhost:8080/stats` setelah selesai untuk melihat ribuan duplikat yang sukses ditolak).*

### 3. Persistensi Data (Crash Recovery Test)

Membuktikan bahwa rekam jejak deduplikasi aman di *Docker Named Volumes* meskipun kontainer mengalami *crash* atau dihapus.

1. Matikan dan hancurkan kontainer:
```bash
docker compose down

```


2. Nyalakan kembali sistem:
```bash
docker compose up -d

```


3. Buka halaman metrik (`http://localhost:8080/stats`). Data historis (seperti jumlah log yang telah diproses) akan tetap utuh, membuktikan sistem siap mencegah repromrosesan data lama.

