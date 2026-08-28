import os
import random
import io
from pathlib import Path
from PIL import Image
import streamlit as st

# -----------------------------------------------------------------------------
# TETAPAN HALAMAN STREAMLIT
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SpriteStudio Marker - LPC Character Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# KONFIGURASI HIRARKI & SPESIFIKASI LPC (64x64 GRID)
# -----------------------------------------------------------------------------
LPC_LAYER_ORDER = [
    'shadow', 'body', 'bodies', 'eyes', 'head', 'facial', 'beards', 'hair',
    'legs', 'feet', 'torso', 'armour', 'arms', 'hands', 'wrists', 'bracers',
    'cape', 'backpack', 'quiver', 'shield', 'hat', 'tools', 'wings', 'tail'
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
# FUNGSI IMBASAN FOLDER ASET TEMPATAN
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def scan_lpc_directory(base_dir: str):
    """
    Mengimbas folder spritesheets tempatan dan mengkelaskan semua fail .png
    mengikut sub-folder utama (category).
    """
    catalog = {}
    base_path = Path(base_dir)

    if not base_path.exists():
        return catalog

    for file_path in base_path.rglob("*.png"):
        # Ambil nama kategori dari nama folder induk
        category = file_path.parent.name.lower()
        if category == 'bodies':
            category = 'body'

        if category not in catalog:
            catalog[category] = {}

        # Simpan laluan fail penuh dengan kunci nama fail
        rel_key = str(file_path.relative_to(base_path))
        catalog[category][rel_key] = str(file_path)

    return catalog

# -----------------------------------------------------------------------------
# FUNGSI GABUNGAN LAPISAN PNG (COMPOSITING ENGINE)
# -----------------------------------------------------------------------------
def composite_spritesheet(selected_paths: list) -> Image.Image:
    """
    Melapiskan imej PNG secara bertindih menggunakan mod RGBA Pillow.
    """
    canvas = Image.new("RGBA", (SHEET_WIDTH, SHEET_HEIGHT), (0, 0, 0, 0))

    for path in selected_paths:
        if path and os.path.exists(path):
            try:
                layer_img = Image.open(path).convert("RGBA")
                # Pastikan saiz imej mematuhi piawaian LPC 832x1344
                if layer_img.size == (SHEET_WIDTH, SHEET_HEIGHT):
                    canvas = Image.alpha_composite(canvas, layer_img)
                else:
                    # Ubah saiz jika terdapat sedikit perbezaan
                    layer_img = layer_img.resize((SHEET_WIDTH, SHEET_HEIGHT), Image.Resampling.NEAREST)
                    canvas = Image.alpha_composite(canvas, layer_img)
            except Exception as e:
                pass

    return canvas

def extract_frame(sheet: Image.Image, row: int, frame_idx: int) -> Image.Image:
    """
    Memotong bingkai 64x64 piksel dari spritesheet gabungan.
    """
    left = frame_idx * 64
    top = row * 64
    right = left + 64
    bottom = top + 64
    return sheet.crop((left, top, right, bottom))

def generate_gif(sheet: Image.Image, anim_name: str, direction_idx: int) -> bytes:
    """
    Menjana animasi GIF dalam memori untuk pratonton pantas.
    """
    anim_info = LPC_ANIM_MAP[anim_name]
    row = anim_info["rowStart"] if anim_name == "Hurt/Die (6 Frame)" else anim_info["rowStart"] + direction_idx
    frames = []

    for f in range(anim_info["frames"]):
        frame_img = extract_frame(sheet, row, f)
        # Besarkan saiz 4x (256x256) supaya tajam pada paparan UI
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
st.caption("Penjana Watak 2D NPC Terbina Menggunakan Streamlit & Python Pillow Engine")

# SIDEBAR: KETETAPAN FOLDER & KONTROL
with st.sidebar:
    st.header("⚙️ Tetapan Folder & Lapisan")

    default_folder = "./spritesheets"
    if not os.path.exists(default_folder):
        default_folder = "."

    folder_path = st.text_input("📁 Laluan Folder Spritesheets:", value=default_folder)

    catalog = scan_lpc_directory(folder_path)

    if not catalog:
        st.error(f"Folder tidak ditemui atau kosong di: `{folder_path}`")
        st.info("Pastikan laluan folder menunjuk ke direktori yang mempunyai fail `.png` LPC.")
    else:
        st.success(f"Berjaya imbas {len(catalog)} kategori lapisan!")

    st.markdown("---")
    
    # BUTANG RANDOMIZE NPC
    if st.button("🎲 Randomize NPC Watak", use_container_width=True, type="primary"):
        st.session_state['random_trigger'] = True

    st.markdown("### 👕 Pemilihan Pakaian & Anggota")

    # Susun kategori mengikut hirarki LPC
    sorted_categories = sorted(
        catalog.keys(),
        key=lambda c: LPC_LAYER_ORDER.index(c) if c in LPC_LAYER_ORDER else 99
    )

    selected_files = {}

    for cat in sorted_categories:
        options = ["-- Tiada / Kosong --"] + list(catalog[cat].keys())

        # Logik Rawak jika butang ditekan
        if st.session_state.get('random_trigger', False):
            if random.random() < 0.85:
                default_idx = random.randint(1, len(options) - 1)
            else:
                default_idx = 0
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

    # Reset trigger rawak
    if 'random_trigger' in st.session_state:
        st.session_state['random_trigger'] = False

# SUSUNAN SELEKSI IMEJ MENGIKUT Z-INDEX LPC
ordered_image_paths = []
for cat in LPC_LAYER_ORDER:
    if cat in selected_files and selected_files[cat]:
        ordered_image_paths.append(selected_files[cat])

# Tambah mana-mana kategori lebihan yang tidak termasuk dalam hirarki standard
for cat, pth in selected_files.items():
    if cat not in LPC_LAYER_ORDER and pth:
        ordered_image_paths.append(pth)

# MAIN PANEL: PRATONTON & EKSPORT
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🎬 Tetapan Animasi & Arah")

    anim_name = st.selectbox("Pilih Jenis Animasi:", list(LPC_ANIM_MAP.keys()))
    direction_name = st.selectbox("Pilih Arah Pandangan:", list(DIRECTION_MAP.keys()))
    direction_idx = DIRECTION_MAP[direction_name]

    # BINA COMPOSITED SPRITESHEET IN-MEMORY
    composited_sheet = composite_spritesheet(ordered_image_paths)

    # MENJANA PRATONTON GIF
    gif_bytes = generate_gif(composited_sheet, anim_name, direction_idx)

    st.markdown("#### 👁️ Pratonton Animasi NPC (Live Preview)")
    st.image(gif_bytes, caption=f"Animasi: {anim_name} | {direction_name}", width=256)

with col2:
    st.subheader("🖼️ Spritesheet Tergabung Penuh")
    st.image(composited_sheet, caption="Full LPC Spritesheet Matrix (832 x 1344 px)", use_column_width=True)

st.markdown("---")
st.subheader("📥 Muat Turun Aset NPC")

dl_col1, dl_col2, dl_col3 = st.columns(3)

# 1. MUAT TURUN FULL PNG SHEET
sheet_buf = io.BytesIO()
composited_sheet.save(sheet_buf, format="PNG")
sheet_bytes = sheet_buf.getvalue()

dl_col1.download_button(
    label="⬇️ Muat Turun Spritesheet PNG (832x1344)",
    data=sheet_bytes,
    file_name="npc_lpc_character_sheet.png",
    mime="image/png",
    use_container_width=True
)

# 2. MUAT TURUN ANIMATED GIF
dl_col2.download_button(
    label="⬇️ Muat Turun Animasi GIF",
    data=gif_bytes,
    file_name="npc_animation.gif",
    mime="image/gif",
    use_container_width=True
)

# 3. MUAT TURUN SINGLE FRAME 64x64
anim_info = LPC_ANIM_MAP[anim_name]
row_idx = anim_info["rowStart"] if anim_name == "Hurt/Die (6 Frame)" else anim_info["rowStart"] + direction_idx
single_frame = extract_frame(composited_sheet, row_idx, 0)
frame_buf = io.BytesIO()
single_frame.save(frame_buf, format="PNG")

dl_col3.download_button(
    label="⬇️ Muat Turun Bingkai 64x64 Single PNG",
    data=frame_buf.getvalue(),
    file_name="npc_frame_64x64.png",
    mime="image/png",
    use_container_width=True
)