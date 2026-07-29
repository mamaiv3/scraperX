# GdLotto Scraper

Aplikasi Streamlit yang ringkas — fokus tunggal untuk **scrape** keputusan 4D
(1st Prize) dari gdlotto.net dan simpan ke `data.txt`.

## Fungsi

- Pilih julat tarikh ("Dari" → "Hingga")
- Klik **Scrape Sekarang** — app akan tarik nombor 1st Prize bagi setiap
  tarikh dalam julat tersebut secara serentak (thread pool)
- Hasil disimpan automatik ke `data/data.txt` (format `YYYY-MM-DD NNNN`)
- Tarikh sedia ada dilangkau (tiada pendua)
- Butang **Muat Turun data.txt** untuk simpan fail ke komputer anda

Tiada fungsi analisis/ramalan — hanya scraper + simpan/muat turun.

## Run tempatan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy ke Streamlit Cloud

1. Push folder ini ke satu GitHub repo baru
2. Di [share.streamlit.io](https://share.streamlit.io), pilih repo tersebut,
   tetapkan main file ke `app.py`, deploy
3. `data/data.txt` akan tercipta/terkemas kini di dalam storan app semasa ia
   berjalan — muat turun secara berkala jika mahu simpan kekal, kerana
   storan Streamlit Cloud bersifat sementara (reset bila app di-restart/redeploy)

## Format data/data.txt

```
2025-01-26 7550
2025-01-27 5976
2025-01-28 6408
```
