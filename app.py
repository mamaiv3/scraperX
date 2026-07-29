"""
GdLottoX Scraper
----------------
Aplikasi ringkas untuk scrape keputusan 4D (1st Prize) dari gdlotto.net
dan simpan terus ke data.txt (format: YYYY-MM-DD NNNN, satu baris = satu tarikh).

Fokus tunggal: scrape + simpan/muat turun. Tiada fungsi lain.
"""

import concurrent.futures
import os
from datetime import date, datetime, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup

DATA_FILE = "data/data.txt"
MAX_WORKERS = 8

st.set_page_config(page_title="GdLotto Scraper", page_icon="🎯", layout="centered")


# ---------------------------------------------------------------------------
# Fungsi teras
# ---------------------------------------------------------------------------

def get_1st_prize(date_str: str):
    """Ambil nombor 1st Prize (4 digit) untuk satu tarikh dari gdlotto.net."""
    url = f"https://gdlotto.net/results/ajax/_result.aspx?past=1&d={date_str}"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("span", id="1stPz")
        txt = tag.text.strip() if tag else ""
        return txt if txt.isdigit() and len(txt) == 4 else None
    except Exception:
        return None


def load_existing(file_path: str = DATA_FILE) -> dict:
    """Baca data.txt sedia ada -> dict {tarikh: nombor}."""
    if not os.path.exists(file_path):
        return {}
    result = {}
    with open(file_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
                result[parts[0]] = parts[1]
    return result


def save_data(data: dict, file_path: str = DATA_FILE):
    """Tulis semula data.txt, tersusun ikut tarikh."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        for d in sorted(data.keys()):
            f.write(f"{d} {data[d]}\n")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🎯 GdLotto Scraper")
st.caption("Scrape keputusan 4D dari gdlotto.net → data.txt")

with st.expander("ℹ️ Info ringkas", expanded=True):
    st.markdown(
        "- Tarik nombor **1st Prize** (4 digit) bagi setiap tarikh dari **gdlotto.net**.\n"
        "- Disimpan dalam `data.txt`, format `YYYY-MM-DD NNNN` per baris.\n"
        "- Tarikh yang sudah ada dalam `data.txt` akan dilangkau (tiada pendua).\n"
        "- Nak scrape sejarah penuh? Tukar sahaja 'Dari tarikh' ke lebih awal."
    )

existing = load_existing()
if existing:
    st.info(f"📄 data.txt semasa: **{len(existing)}** rekod ({min(existing)} → {max(existing)})")
else:
    st.info("📄 data.txt masih kosong.")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Dari tarikh", value=date.today() - timedelta(days=90))
with col2:
    end_date = st.date_input("Hingga tarikh", value=date.today())

if st.button("🚀 Scrape Sekarang", use_container_width=True, type="primary"):
    if start_date > end_date:
        st.error("Tarikh 'Dari' mesti sebelum atau sama dengan tarikh 'Hingga'.")
    else:
        existing = load_existing()

        dates_to_check = []
        current = start_date
        while current <= end_date:
            ds = current.strftime("%Y-%m-%d")
            if ds not in existing:
                dates_to_check.append(ds)
            current += timedelta(days=1)

        total = len(dates_to_check)
        if total == 0:
            st.info("Semua tarikh dalam julat ini sudah ada dalam data.txt. ✅")
        else:
            progress = st.progress(0)
            status = st.empty()
            found = 0
            done = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_date = {executor.submit(get_1st_prize, ds): ds for ds in dates_to_check}
                for future in concurrent.futures.as_completed(future_to_date):
                    ds = future_to_date[future]
                    done += 1
                    try:
                        prize = future.result()
                    except Exception:
                        prize = None
                    if prize:
                        existing[ds] = prize
                        found += 1
                    progress.progress(done / total)
                    status.text(f"Memproses... ({done}/{total}) — {found} rekod ditemui")

            save_data(existing)
            status.empty()
            progress.empty()
            st.success(f"✅ Selesai! {found} rekod baru ditambah. Jumlah keseluruhan: {len(existing)} rekod.")

# ---------------------------------------------------------------------------
# Preview + Muat turun
# ---------------------------------------------------------------------------

existing = load_existing()
if existing:
    st.divider()
    st.subheader("📋 Pratonton (10 terkini)")
    sorted_items = sorted(existing.items(), reverse=True)
    preview_text = "\n".join(f"{d}  {n}" for d, n in sorted_items[:10])
    st.text(preview_text + ("\n..." if len(existing) > 10 else ""))

    with open(DATA_FILE, "rb") as f:
        st.download_button(
            "💾 Muat Turun data.txt",
            data=f,
            file_name="data.txt",
            mime="text/plain",
            use_container_width=True,
        )
