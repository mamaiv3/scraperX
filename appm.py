import os
import random
import io
import requests
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
# KONFIGURASI HIRARKI & SPESIFIKASI LPC
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
# MEMBACA FOLDER DARI GITHUB API DIRECTLY
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner="Memuat turun fail dari GitHub Folder...")
def fetch_github_folder_contents(owner: str, repo: str, branch: str, path: str):
    """
    Mendapatkan senarai fail dan memuat turun imej dari folder GitHub.
    """
    catalog = {}
    images_db = {}
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        items = response.json()
        
        for item in items:
            # Jika item ialah item fail PNG
            if item.get("type") == "file" and item.get("name").endswith(".png"):
                file_name = item["name"]
                download_url = item["download_url"]
                
                # Mengkategorikan fail (contoh: 'body', 'hair', dsb.)
                category = file_name.split("_")[0].lower() if "_" in file_name else "uncategorized"
                if category == 'bodies':
                    category = 'body'
                
                if category not in catalog:
                    catalog[category] = {}
                
                catalog[category][file_name] = download_url
                
            # Jika terdapat sub-folder di dalamnya
            elif item.get("type") == "dir":
                sub_catalog, sub_db = fetch_github_folder_contents(owner, repo, branch, item["path"])
                for cat, files in sub_catalog.items():
                    if cat not in catalog:
                        catalog[cat] = {}
                    catalog[cat].update(files)
                    
    except Exception as e:
        st.error(f"Gagal memuat turun folder dari GitHub API: {e}")
        
    return catalog, images_db

@st.cache_data(show_spinner="Memuat turun imej...")
def load_image_from_url(url: str):
    res = requests.get(url, timeout=15)
    return res.content

# -----------------------------------------------------------------------------
# FUNGSI GABUNGAN LAPISAN PNG
# -----------------------------------------------------------------------------
def composite_spritesheet(selected_urls: list) -> Image.Image:
    canvas = Image.new("RGBA", (SHEET_WIDTH, SHEET_HEIGHT), (0, 0, 0, 0))

    for url in selected_urls:
        if url:
            try:
                img_bytes = load_image_from_url(url)
                layer_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
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
st.caption("Penjana Watak 2D NPC Terbina Menggunakan GitHub Folder API")

with st.sidebar:
    st.header("⚙️ Tetapan Folder GitHub")

    # Maklumat Repositori Anda
    owner = "mamaiv3"
    repo = "Universal-LPC-Spritesheet-Character-Generator"
    branch = "master"
    folder_path = st.text_input("📁 Laluan Folder GitHub:", value="sheet_definitions")

    catalog, _ = fetch_github_folder_contents(owner, repo, branch, folder_path)

    if catalog:
        st.success("Berjaya membaca folder GitHub!")
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
    else:
        st.error("Tiada fail `.png` dijumpai di dalam folder tersebut.")

ordered_urls = []
if catalog:
    for cat in LPC_LAYER_ORDER:
        if cat in selected_files and selected_files[cat]:
            ordered_urls.append(selected_files[cat])

    for cat, url in selected_files.items():
        if cat not in LPC_LAYER_ORDER and url:
            ordered_urls.append(url)

col1, col2 = st.columns([1, 1])

if catalog and ordered_urls:
    with col1:
        st.subheader("🎬 Tetapan Animasi & Arah")

        anim_name = st.selectbox("Pilih Jenis Animasi:", list(LPC_ANIM_MAP.keys()))
        direction_name = st.selectbox("Pilih Arah Pandangan:", list(DIRECTION_MAP.keys()))
        direction_idx = DIRECTION_MAP[direction_name]

        composited_sheet = composite_spritesheet(ordered_urls)
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