import os
import random
import io
import zipfile
import requests
from PIL import Image
import streamlit as st

# -----------------------------------------------------------------------------
# TETAPAN HALAMAN STREAMLIT
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SpriteStudio Marker - LPC Character Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# KONFIGURASI HIRARKI & SPESIFIKASI LPC
# -----------------------------------------------------------------------------
LPC_LAYER_ORDER = [
    'body', 'head', 'headwear', 'hair', 'arms', 'torso', 
    'legs', 'feet', 'tools', 'weapons'
]

LPC_ANIM_MAP = {
    "Walk Cycle (9 Frame)": {"rowStart": 8, "frames": 9},
    "Spellcast (7 Frame)": {"rowStart": 0, "frames": 7},
    "Thrust (8 Frame)": {"rowStart": 4, "frames": 8},
    "Slash (6 Frame)": {"rowStart": 12, "frames": 6},
    "Shoot (13 Frame)": {"rowStart": 16, "frames": 13},
    "Hurt/Die (6 Frame)": {"rowStart": 20, "frames": 6}
}

DIRECTION_MAP = {
    "South (Selatan)": 2,
    "North (Utara)": 0,
    "West (Barat)": 1,
    "East (Timur)": 3
}

SHEET_WIDTH = 832
SHEET_HEIGHT = 1344

# -----------------------------------------------------------------------------
# MUAT TURUN & EKSTRAK ZIP DARI REPO (TANPA HAD GITHUB API)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner="Memuat turun & memproses folder aset dari repositori...")
def load_repo_assets():
    """
    Memuat turun repositori ZIP mentah terus dari GitHub.
    Kaedah ini tidak melepasi had API GitHub (No Rate Limit).
    """
    zip_url = "https://github.com/mamaiv3/Universal-LPC-Spritesheet-Character-Generator/archive/refs/heads/master.zip"
    catalog = {}
    images_db = {}
    
    try:
        res = requests.get(zip_url, timeout=60)
        res.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(res.content)) as z:
            for file_info in z.infolist():
                filename = file_info.filename
                
                # Hanya ambil fail .png di dalam folder sheet_definitions
                if "sheet_definitions/" in filename and filename.endswith(".png"):
                    parts = filename.split("/")
                    
                    # Cari indeks folder sheet_definitions
                    if "sheet_definitions" in parts:
                        idx = parts.index("sheet_definitions")
                        if len(parts) > idx + 2:
                            cat = parts[idx + 1]
                            file_name = parts[-1]
                            
                            if cat not in catalog:
                                catalog[cat] = {}
                            
                            catalog[cat][file_name] = filename
                            images_db[filename] = z.read(filename)
                            
        return catalog, images_db
    except Exception as e:
        st.error(f"Gagal memuat turun fail aset: {e}")
        return {}, {}

# -----------------------------------------------------------------------------
# FUNGSI GABUNGAN LAPISAN PNG
# -----------------------------------------------------------------------------
def composite_spritesheet(selected_keys: list, images_db: dict) -> Image.Image:
    canvas = Image.new("RGBA", (SHEET_WIDTH, SHEET_HEIGHT), (0, 0, 0, 0))

    for key in selected_keys:
        if key and key in images_db:
            try:
                layer_img = Image.open(io.BytesIO(images_db[key])).convert("RGBA")
                if layer_img.size != (SHEET_WIDTH, SHEET_HEIGHT):
                    layer_img = layer_img.resize((SHEET_WIDTH, SHEET_HEIGHT), Image.Resampling.NEAREST)
                canvas = Image.alpha_composite(canvas, layer_img)
            except Exception:
                pass

    return canvas

def extract_frame(sheet: Image.Image, row: int, frame_idx: int) -> Image.Image:
    left = frame_idx * 64
    top = row * 64
    return sheet.crop((left, top, left + 64, top + 64))

def generate_gif(sheet: Image.Image, anim_name: str, direction_idx: int) -> bytes:
    anim_info = LPC_ANIM_MAP[anim_name]
    row = anim_info["rowStart"] if anim_name == "Hurt/Die (6 Frame)" else anim_info["rowStart"] + direction_idx
    frames = []

    for f in range(anim_info["frames"]):
        frame_img = extract_frame(sheet, row, f)
        resized_frame = frame_img.resize((256, 256), Image.Resampling.NEAREST)
        frames.append(resized_frame)

    buf = io.BytesIO()
    if frames:
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=120,
            loop=0,
            disposal=2
        )
    return buf.getvalue()

# -----------------------------------------------------------------------------
# UTAMA: ANTARAMUKA STREAMLIT
# -----------------------------------------------------------------------------
st.title("🎨 SpriteStudio Marker - LPC Character Studio")
st.caption("Penjana Watak 2D NPC Terbina")

catalog, images_db = load_repo_assets()

with st.sidebar:
    st.header("⚙️ Tetapan Folder GitHub")

    if catalog:
        st.success("Berjaya membaca folder aset dari GitHub!")
        st.markdown("---")

        if st.button("🎲 Randomize NPC Watak", use_container_width=True, type="primary"):
            st.session_state['random_trigger'] = True

        st.markdown("### 👕 Pemilihan Pakaian & Anggota")

        sorted_categories = sorted(
            catalog.keys(),
            key=lambda c: LPC_LAYER_ORDER.index(c) if c in LPC_LAYER_ORDER else 99
        )

        selected_files = {}

        for cat in sorted_categories:
            options = ["-- Tiada / Kosong --"] + list(catalog[cat].keys())

            if st.session_state.get('random_trigger', False):
                default_idx = random.randint(1, len(options) - 1) if random.random() < 0.85 else 0
                st.session_state[f"select_{cat}"] = options[default_idx]

            selected_val = st.selectbox(
                f"Lapisan: {cat.capitalize()}",
                options=options,
                key=f"select_{cat}"
            )

            if selected_val != "-- Tiada / Kosong --":
                selected_files[cat] = catalog[cat][selected_val]
            else:
                selected_files[cat] = None

        if 'random_trigger' in st.session_state:
            st.session_state['random_trigger'] = False

ordered_keys = []
if catalog:
    for cat in LPC_LAYER_ORDER:
        if cat in selected_files and selected_files[cat]:
            ordered_keys.append(selected_files[cat])

    for cat, key in selected_files.items():
        if cat not in LPC_LAYER_ORDER and key:
            ordered_keys.append(key)

col1, col2 = st.columns([1, 1])

if catalog and ordered_keys:
    with col1:
        st.subheader("🎬 Tetapan Animasi & Arah")

        anim_name = st.selectbox("Pilih Jenis Animasi:", list(LPC_ANIM_MAP.keys()))
        direction_name = st.selectbox("Pilih Arah Pandangan:", list(DIRECTION_MAP.keys()))
        direction_idx = DIRECTION_MAP[direction_name]

        composited_sheet = composite_spritesheet(ordered_keys, images_db)
        gif_bytes = generate_gif(composited_sheet, anim_name, direction_idx)

        st.markdown("#### 👁️ Pratonton Animasi NPC (Live Preview)")
        st.image(gif_bytes, caption=f"Animasi: {anim_name} | {direction_name}", width=256)

    with col2:
        st.subheader("🖼️ Spritesheet Tergabung Penuh")
        st.image(composited_sheet, caption="Full LPC Spritesheet Matrix (832 x 1344 px)", use_column_width=True)

    st.markdown("---")
    st.subheader("📥 Muat Turun Aset NPC")

    dl_col1, dl_col2, dl_col3 = st.columns(3)

    sheet_buf = io.BytesIO()
    composited_sheet.save(sheet_buf, format="PNG")

    dl_col1.download_button(
        label="⬇️ Muat Turun Spritesheet PNG",
        data=sheet_buf.getvalue(),
        file_name="npc_lpc_character_sheet.png",
        mime="image/png",
        use_container_width=True
    )

    dl_col2.download_button(
        label="⬇️ Muat Turun Animasi GIF",
        data=gif_bytes,
        file_name="npc_animation.gif",
        mime="image/gif",
        use_container_width=True
    )

    anim_info = LPC_ANIM_MAP[anim_name]
    row_idx = anim_info["rowStart"] if anim_name == "Hurt/Die (6 Frame)" else anim_info["rowStart"] + direction_idx
    single_frame = extract_frame(composited_sheet, row_idx, 0)
    frame_buf = io.BytesIO()
    single_frame.save(frame_buf, format="PNG")

    dl_col3.download_button(
        label="⬇️ Muat Turun Frame 64x64",
        data=frame_buf.getvalue(),
        file_name="npc_frame_64x64.png",
        mime="image/png",
        use_container_width=True
    )