import streamlit as st
import folium
from streamlit_folium import st_folium
import rasterio
import pyproj
import geopandas as gpd
from shapely.geometry import Point
import numpy as np
from PIL import Image
import os
import yaml
import base64
import plotly.graph_objects as go
from rasterstats import zonal_stats

st.set_page_config(page_title="Indeks Risiko Banjir Surabaya", layout="wide", initial_sidebar_state="collapsed")

from datetime import datetime

st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Spectral:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@500;700&display=swap');
    
    .stApp { background-color: #F4F1EA !important; font-family: 'IBM Plex Sans', sans-serif !important; color: #2B2A28 !important; }
    .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp td, .stApp th {
        color: #2B2A28 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    
    .block-container {
        padding-top: 96px !important; /* Header height */
        padding-bottom: 35px !important; /* Footer height */
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
    }
    
    header {visibility: hidden;}
    
    .enterprise-header {
        background: #FFFFFF;
        height: 96px;
        box-sizing: border-box;
        position: fixed; top: 0; left: 0; right: 0; z-index: 999999;
        display: flex; justify-content: center; align-items: center;
        padding: 16px 20px 14px 20px; border-bottom: 1px solid #E5E7EB;
    }
    .header-title-box { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; gap: 6px; }
    .header-title { font-family: 'Plus Jakarta Sans', sans-serif !important; font-size: 42px; font-weight: 700; margin: 0 !important; padding: 0 !important; color: #111827 !important; letter-spacing: -0.5px; line-height: 1 !important; }
    .header-subtitle { font-family: 'Plus Jakarta Sans', sans-serif !important; font-size: 16px; color: #6B7280; margin: 0 !important; padding: 0 !important; font-weight: 500; letter-spacing: 1.2px; line-height: 1 !important; }
    
    /* Force map to fill the vertical space */
    div.element-container:has(iframe),
    div[data-testid="stIFrame"],
    iframe { 
        position: fixed !important;
        top: 96px !important;
        bottom: 32px !important;
        left: 0 !important;
        right: 0 !important;
        width: 100vw !important;
        height: calc(100vh - 128px) !important;
        border-radius: 0 !important; 
        border: none !important; 
        margin: 0 !important; 
        z-index: 0 !important;
    }
    
    .ranking-container { max-height: calc(100vh - 380px); overflow-y: auto; padding: 0 10px; }
    .ranking-container::-webkit-scrollbar { width: 5px; }
    .ranking-container::-webkit-scrollbar-thumb { background: #DDD6C7; border-radius: 3px; }
    
    .district-card {
        background: #FBF9F4;
        border: 1px solid #DDD6C7; border-radius: 6px;
        padding: 12px; margin-bottom: 8px;
        transition: transform 0.2s ease;
    }
    .district-card:hover { transform: translateY(-2px); border-color: #8A8375; }
    
    .dc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .dc-name { font-family: 'Spectral', serif !important; font-weight: 600; font-size: 14px; color: #2B2A28 !important; }
    
    .badge { font-family: 'IBM Plex Mono', monospace !important; padding: 3px 8px; border-radius: 4px; font-size: 9px; font-weight: 600; letter-spacing: 0.8px; display: inline-flex; align-items: center; gap: 4px; text-transform: uppercase; }
    .badge-high { background: rgba(220, 38, 38, 0.12); color: #DC2626; border: 1px solid rgba(220, 38, 38, 0.25); }
    .badge-med { background: rgba(245, 158, 11, 0.12); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.25); }
    .badge-low { background: rgba(22, 163, 74, 0.12); color: #16A34A; border: 1px solid rgba(22, 163, 74, 0.25); }
    
    .dc-score { font-family: 'IBM Plex Mono', monospace !important; font-size: 18px; font-weight: 600; color: #2B2A28 !important; margin-bottom: 8px; display: flex; align-items: baseline; gap: 8px; }
    .dc-score-label { font-family: 'IBM Plex Mono', monospace !important; font-size: 10px; color: #8A8375; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    
    .mini-bar-bg { height: 5px; background: #DDD6C7; border-radius: 3px; overflow: hidden; width: 100%; }
    .mini-bar-fill { height: 100%; border-radius: 3px; transition: width 1s ease-in-out; }
    
    /* Dialog Styling — Clean Modern UI */
    div[data-testid="stDialog"],
    div[data-testid="stDialog"][role="dialog"] {
        max-width: 850px !important;
        width: 100% !important;
        height: auto !important;
        max-height: calc(100vh - 180px) !important; /* Memberi ruang di bawah */
        margin: 110px auto 40px auto !important; /* Jarak 110px dari atas, 40px dari bawah */
        border-radius: 12px !important;
        background: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
        overflow-y: auto !important;
        animation: modalScaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        font-family: 'Inter', 'IBM Plex Sans', sans-serif !important;
    }
    
    /* Override Streamlit's default dark mode text colors inside the white dialog */
    div[data-testid="stDialog"] * {
        color: #374151;
    }
    div[data-testid="stDialog"] h1,
    div[data-testid="stDialog"] h2,
    div[data-testid="stDialog"] h3 {
        color: #111827 !important;
    }
    div[data-testid="stDialog"] button svg {
        fill: #6B7280 !important;
        color: #6B7280 !important;
    }
    
    div[data-testid="stDialog"] > div {
        background: transparent !important;
        padding: 24px 32px 24px 32px !important;
    }
    /* Force all nested containers inside dialog to be transparent */
    div[data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stDialog"] [data-testid="stVerticalBlock"],
    div[data-testid="stDialog"] [data-testid="column"],
    div[data-testid="stDialog"] section,
    div[data-testid="stDialog"] > div > div {
        background: transparent !important;
        background-color: transparent !important;
    }
    @keyframes modalScaleIn {
        0% { opacity: 0; transform: scale(0.97) translateY(8px); }
        100% { opacity: 1; transform: scale(1) translateY(0); }
    }
    div[data-testid="stModalOverlay"],
    div[data-testid="stModal"] {
        background-color: rgba(17, 24, 39, 0.4) !important;
        backdrop-filter: blur(2px) !important;
        display: flex !important;
        align-items: flex-start !important; /* Modal dimulai dari atas (kemudian didorong margin) */
        justify-content: center !important;
    }
    
    /* Native Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; border-bottom: 1px solid #E5E7EB; }
    .stTabs [data-baseweb="tab"] { color: #6B7280; font-weight: 600; font-family: 'Inter', sans-serif; font-size: 14px; padding-bottom: 12px; }
    .stTabs [aria-selected="true"] { color: #3B82F6 !important; border-bottom: 2px solid #3B82F6 !important; }
    
    /* KPI Cards */
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 12px; }
    .kpi-card {
        background: #FFFFFF; border: 1px solid #E5E7EB;
        border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; justify-content: center;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        border-left: 3px solid #3B82F6;
    }
    .kpi-card.cat-low { border-left-color: #16A34A; }
    .kpi-card.cat-med { border-left-color: #F59E0B; }
    .kpi-card.cat-high { border-left-color: #DC2626; }
    
    .kpi-label { font-family: 'Inter', sans-serif !important; font-size: 10px; color: #6B7280; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .kpi-value { font-family: 'Inter', sans-serif !important; font-size: 18px; color: #111827; font-weight: 700; line-height: 1.2; }
    .kpi-subtext { font-family: 'Inter', sans-serif !important; font-size: 10px; color: #6B7280; margin-top: 2px; }
    
    /* Parameter Progress Bars */
    .param-item { margin-bottom: 16px; }
    .param-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; color: #111827; font-size: 12px; font-weight: 500; }
    .param-icon { margin-right: 8px; color: #3B82F6; width: 20px; text-align: center; }
    .param-bar-bg { height: 6px; background: #E5E7EB; border-radius: 3px; overflow: hidden; width: 100%; }
    .param-bar-fill { height: 100%; border-radius: 3px; transition: width 1s ease-in-out; }
    
    /* Panel Cards (Gauge & Rekomendasi) */
    .panel-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        height: 100%;
    }
    .panel-title {
        font-family: 'Inter', sans-serif !important; font-size: 14px; font-weight: 600; color: #111827; margin-bottom: 12px;
    }
    
    /* Recommendation Card Items */
    .rec-item { 
        background: #F9FAFB;
        border-left: 2px solid #3B82F6;
        padding: 10px 12px;
        margin-bottom: 8px;
        color: #374151; 
        font-size: 12px; 
        font-family: 'Inter', sans-serif;
        border-radius: 0 4px 4px 0;
    }
    
    /* Alert Box */
    .alert-box {
        background: #EFF6FF;
        border-radius: 6px;
        padding: 16px;
        display: flex;
        gap: 12px;
        align-items: center;
        margin-top: 10px;
    }
    .alert-box.alert-low { background: #EFF6FF; color: #1D4ED8; }
    .alert-box.alert-med { background: #FEF3C7; color: #B45309; }
    .alert-box.alert-high { background: #FEE2E2; color: #B91C1C; }
    
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="enterprise-header">
    <div class="header-title-box">
        <h2 class="header-title">Indeks Risiko Banjir</h2>
        <p class="header-subtitle">Kota Surabaya &bull; Peta Analisis Multi-Kriteria</p>
    </div>
</div>
<div style="height: 20px;"></div>
""", unsafe_allow_html=True)

@st.cache_data
def load_config():
    # Load config file
    with open('config.yaml', 'r') as f: return yaml.safe_load(f)

cfg = load_config()
interim_dir = cfg['paths']['interim']
final_dir = cfg['paths']['final']
raw_dir = cfg['paths']['raw_data']

final_tif = os.path.join(final_dir, 'peta_risiko_final.tif')
boundary_path = os.path.join(raw_dir, cfg['files']['boundary'])

@st.cache_data
def get_boundary_data():
    boundary = gpd.read_file(boundary_path)
    boundary_utm = boundary.to_crs(cfg['project']['crs'])
    return boundary, boundary_utm

@st.cache_data
def get_map_center(_boundary):
    centroid = _boundary.to_crs("EPSG:4326").geometry.unary_union.centroid
    return [centroid.y, centroid.x]

@st.cache_data
def generate_colormap_image(tif_path):
    if not os.path.exists(tif_path): return None, None
    with rasterio.open(tif_path) as src:
        data = src.read(1)
        nodata = src.nodata
        bounds = src.bounds
        
    transformer = pyproj.Transformer.from_crs(cfg['project']['crs'], "EPSG:4326", always_xy=True)
    min_lon, min_lat = transformer.transform(bounds.left, bounds.bottom)
    max_lon, max_lat = transformer.transform(bounds.right, bounds.top)
    
    valid_mask = data != nodata
    rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)
    
    colors = {
        1: [22, 163, 74, 255], 2: [22, 163, 74, 255], 3: [245, 158, 11, 255], 
        4: [220, 38, 38, 255], 5: [220, 38, 38, 255]    
    }
    for val, color in colors.items():
        rgba[valid_mask & (data >= val - 0.5) & (data < val + 0.5)] = color
        
    img = Image.fromarray(rgba)
    img_name = os.path.basename(tif_path).replace('.tif', '_overlay_v2.png')
    img_path_out = os.path.join(final_dir, img_name)
    img.save(img_path_out)
    return img_path_out, [[min_lat, min_lon], [max_lat, max_lon]]

def get_name_column(gdf):
    possible_names = ['KECAMATAN', 'WADMKC', 'NAMOBJ', 'NAME_3', 'NAME_2', 'KEC', 'NAMA']
    for p in possible_names:
        if p in gdf.columns: return p
    for col in gdf.columns:
        if gdf[col].dtype == 'O' and col != 'geometry' and 'ID' not in col.upper() and 'CODE' not in col.upper():
            return col
    # Fallback to the first object column
    for col in gdf.columns:
        if gdf[col].dtype == 'O' and col != 'geometry':
            return col
    return None

@st.cache_data
def compute_zonal_stats():
    _, boundary_utm = get_boundary_data()
    name_col = get_name_column(boundary_utm)
    nodata_val = float(cfg['project']['nodata'])
            
    stats = zonal_stats(boundary_utm, final_tif, stats="mean", nodata=nodata_val)
    results = []
    for i, stat in enumerate(stats):
        if stat['mean'] is not None:
            nama = boundary_utm.iloc[i][name_col] if name_col else f"Area {i+1}"
            results.append({'Kecamatan': nama, 'Skor': stat['mean']})
    results = sorted(results, key=lambda x: x['Skor'], reverse=True)
    return results

@st.cache_data
def compute_district_population():
    _, boundary_utm = get_boundary_data()
    name_col = get_name_column(boundary_utm)
            
    # Gunakan data CSV BPS secara langsung agar angka pop-up 100% akurat
    bps_path = os.path.join(raw_dir, 'Jumlah Penduduk Menurut Kewarganegaraan dan Jenis Kelamin per Kecamatan, 2024.csv')
    if os.path.exists(bps_path):
        import pandas as pd
        df = pd.read_csv(bps_path, skiprows=5, usecols=[0, 3], names=['Kecamatan', 'Total'])
        df = df.dropna()
        df['Kecamatan'] = df['Kecamatan'].str.strip().str.upper()
        csv_dict = dict(zip(df['Kecamatan'], df['Total']))
        
        pop_dict = {}
        for i in range(len(boundary_utm)):
            nama_asli = boundary_utm.iloc[i][name_col] if name_col else f"Area {i+1}"
            nama_upper = nama_asli.strip().upper()
            nama_upper = nama_upper.replace('PABEANCANTIAN', 'PABEAN CANTIAN').replace('KARANG PILANG', 'KARANGPILANG')
            pop_dict[nama_asli] = int(csv_dict.get(nama_upper, 0))
        return pop_dict
        
    # Fallback jika CSV tidak ada (misal menggunakan data lama)
    pop_tif = os.path.join(interim_dir, 'populasi_30m.tif')
    if not os.path.exists(pop_tif):
        return {}
        
    nodata_val = float(cfg['project']['nodata'])
    stats = zonal_stats(boundary_utm, pop_tif, stats="mean", nodata=nodata_val)
    pop_dict = {}
    for i, stat in enumerate(stats):
        nama = boundary_utm.iloc[i][name_col] if name_col else f"Area {i+1}"
        area_km2 = boundary_utm.iloc[i].geometry.area / 1_000_000
        mean_density = stat['mean'] if stat['mean'] is not None else 0
        pop_dict[nama] = int(mean_density * area_km2)
    return pop_dict

@st.cache_resource
def get_transformer():
    return pyproj.Transformer.from_crs("EPSG:4326", cfg['project']['crs'], always_xy=True)

@st.cache_resource
def get_raster_src(tif_path):
    if not os.path.exists(tif_path): return None
    return rasterio.open(tif_path)

def get_pixel_value(lat, lon, tif_path):
    src = get_raster_src(tif_path)
    if src is None: return None
    
    transformer = get_transformer()
    x, y = transformer.transform(lon, lat)
    
    row, col = rasterio.transform.rowcol(src.transform, x, y)
    if 0 <= row < src.height and 0 <= col < src.width:
        window = rasterio.windows.Window(col, row, 1, 1)
        val = src.read(1, window=window)[0, 0]
        if val != src.nodata: return val
    return None

def get_district_name(lat, lon, boundary_utm):
    transformer = get_transformer()
    x, y = transformer.transform(lon, lat)
    pt = Point(x, y)
    name_col = get_name_column(boundary_utm)
    for _, row in boundary_utm.iterrows():
        if row.geometry.contains(pt):
            if name_col:
                return row[name_col]
            return "Wilayah Surabaya"
    return "Tidak Diketahui"

def render_animated_bar(label, icon, val):
    pct = (val / 5.0) * 100
    if val >= 4: color = "#DC2626"
    elif val >= 3: color = "#F59E0B"
    else: color = "#16A34A"
    
    desc_map = {
        "Elevasi (Dataran Rendah)": ["Tinggi (>15m)", "Sedang (10-15m)", "Rendah (5-10m)", "Sangat Rendah (2-5m)", "Pesisir/Datar (<2m)"],
        "Intensitas Curah Hujan": ["Rendah (<1500mm)", "Normal (1500-2000mm)", "Tinggi (2000-2500mm)", "Sangat Tinggi (2500-3000)", "Ekstrem (>3000mm)"],
        "Jarak Sungai": ["Jauh (>1km)", "Sedang (500m-1km)", "Dekat (200-500m)", "Sangat Dekat (50-200m)", "Bantaran (<50m)"],
        "Jenis Tanah": ["Hutan Lebat", "Perkebunan", "Semak/Rumput", "Tanah Gundul", "Permukiman/Kedap Air"],
        "Kepadatan Penduduk": ["Sangat Jarang", "Jarang", "Sedang", "Padat", "Sangat Padat"],
        "Kepadatan Bangunan": ["< 10%", "10 - 30%", "30 - 60%", "60 - 80%", "> 80% (Sangat Padat)"],
        "Fasilitas Kritis": ["Tidak Ada", "Sedikit", "Sedang", "Banyak", "Sangat Banyak/Rentan"]
    }
    
    val_idx = max(0, min(4, int(val) - 1))
    desc_text = desc_map.get(label, [f"{int(val)}/5"] * 5)[val_idx]
    
    st.markdown(f"""
    <div class="param-item" style="margin-bottom: 24px;">
        <div class="param-header">
            <span><i class="{icon} param-icon"></i> {label}</span>
            <span style="font-family: 'IBM Plex Mono', monospace; color: #94A3B8; font-weight: 600; font-size: 12px;">{desc_text}</span>
        </div>
        <div class="param-bar-bg"><div class="param-bar-fill" style="width: {pct}%; background: {color};"></div></div>
    </div>
    """, unsafe_allow_html=True)

@st.experimental_dialog("Analisis Detail Lokasi", width="large")
def show_detail_popup(lat, lon, boundary_utm, pop_dict):
    val = get_pixel_value(lat, lon, final_tif)
    if val is None:
        st.warning("Lokasi berada di luar wilayah Kota Surabaya.")
        return
        
    district = get_district_name(lat, lon, boundary_utm)
    district_pop = pop_dict.get(district, 0)
    formatted_pop = f"{district_pop:,}".replace(",", ".")
    
    elevasi = get_pixel_value(lat, lon, os.path.join(interim_dir, 'elevasi_reclass.tif')) or 1
    hujan = get_pixel_value(lat, lon, os.path.join(interim_dir, 'hujan_reclass.tif')) or 1
    sungai = get_pixel_value(lat, lon, os.path.join(interim_dir, 'sungai_reclass.tif')) or 1
    tanah = get_pixel_value(lat, lon, os.path.join(interim_dir, 'tanah_reclass.tif')) or 1
    populasi = get_pixel_value(lat, lon, os.path.join(interim_dir, 'populasi_reclass.tif')) or 1
    bangunan = get_pixel_value(lat, lon, os.path.join(interim_dir, 'bangunan_reclass.tif')) or 1
    fasum = get_pixel_value(lat, lon, os.path.join(interim_dir, 'fasum_reclass.tif')) or 1
    
    if val >= 3.5:
        cat_text = "TINGGI"
        cat_color = "#DC2626"
        badge_bg = "rgba(220, 38, 38, 0.12)"
        cat_class = "cat-high"
        alert_class = "alert-high"
        alert_icon = "fa-triangle-exclamation"
        alert_text = "Lokasi ini memiliki risiko banjir tinggi. Segera ambil tindakan pencegahan dan mitigasi."
    elif val >= 2.5:
        cat_text = "SEDANG"
        cat_color = "#F59E0B"
        badge_bg = "rgba(245, 158, 11, 0.12)"
        cat_class = "cat-med"
        alert_class = "alert-med"
        alert_icon = "fa-circle-exclamation"
        alert_text = "Lokasi ini memiliki risiko banjir sedang. Perhatikan peringatan dini dari pihak berwenang."
    else:
        cat_text = "RENDAH"
        cat_color = "#16A34A"
        badge_bg = "rgba(22, 163, 74, 0.12)"
        cat_class = "cat-low"
        alert_class = "alert-low"
        alert_icon = "fa-circle-info"
        alert_text = "Lokasi ini memiliki risiko banjir rendah. Tetap waspada dan jaga lingkungan sekitar."
        
    badge = f"<span style='background: {badge_bg}; color: {cat_color}; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; font-family: Inter, sans-serif;'><i class='fa-solid fa-shield-halved'></i> RISIKO {cat_text}</span>"

    st.markdown(f"""
    <div style='display:flex; justify-content:space-between; align-items:flex-start; padding-top: 24px; margin-bottom: 12px;'>
        <div style='display:flex; align-items:center; gap: 16px;'>
            <div style='width: 48px; height: 48px; border-radius: 50%; background: #EFF6FF; color: #3B82F6; display: flex; justify-content: center; align-items: center; font-size: 20px flex-shrink: 0;'>
                <i class='fa-solid fa-location-dot'></i>
            </div>
            <div>
                <h2 style='margin:0; font-size: 24px; font-family: Inter, sans-serif !important; font-weight: 600; color: #111827 !important;'>{district}</h2>
                <p style='margin:0; margin-top: 4px; font-size: 14px; font-family: Inter, sans-serif; color: #6B7280;'>Kecamatan {district}, Kota Surabaya, Jawa Timur</p>
            </div>
        </div>
        <div>{badge}</div>
    </div>
    
    <div class='kpi-grid'>
        <div class='kpi-card'>
            <span class='kpi-label'>Populasi</span>
            <span class='kpi-value'>{formatted_pop}</span>
            <span class='kpi-subtext'>jiwa</span>
        </div>
        <div class='kpi-card'>
            <span class='kpi-label'>Skor Elevasi</span>
            <span class='kpi-value'>{int(elevasi)}/5</span>
            <span class='kpi-subtext'>{"Sangat Tinggi" if elevasi>=4 else "Sedang"}</span>
        </div>
        <div class='kpi-card'>
            <span class='kpi-label'>Skor Risiko</span>
            <span class='kpi-value'>{val:.2f}</span>
            <span class='kpi-subtext'>dari 5.00</span>
        </div>
        <div class='kpi-card {cat_class}'>
            <span class='kpi-label'>Kategori</span>
            <span class='kpi-value' style='color: {cat_color};'>{cat_text}</span>
            <span class='kpi-subtext'>Risiko Banjir</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Ringkasan", "Parameter", "Visualisasi"])
    
    with tab1:
        st.markdown("<div class='panel-title' style='text-align: center;'>Indeks Risiko Banjir</div>", unsafe_allow_html=True)
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = val,
            number = {'font': {'family': 'Inter', 'color': cat_color, 'size': 54}},
            gauge = {
                'axis': {'range': [1, 5], 'tickcolor': '#9CA3AF', 'tickfont': dict(color='#9CA3AF', family='Inter')}, 
                'bar': {'color': cat_color, 'thickness': 0.2},
                'bgcolor': "#F3F4F6",
                'borderwidth': 0,
                'steps': [{'range': [1, 5], 'color': "#F3F4F6"}]
            }
        ))
        fig_gauge.update_layout(height=200, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
        st.markdown("<div style='text-align: center; color: #6B7280; font-size: 13px; font-family: Inter; margin-top: -20px; margin-bottom: 20px;'>dari 5</div>", unsafe_allow_html=True)
            
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("""
        <div style='margin-bottom: 12px; font-family: Inter, sans-serif; font-size: 13px; font-weight: 600; color: #2B2A28; text-transform: uppercase; letter-spacing: 1px;'>
            <i class='fa-solid fa-triangle-exclamation'></i> Komponen Hazard (Bencana Alam)
        </div>
        """, unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="large")
        with c1:
            render_animated_bar("Elevasi (Dataran Rendah)", "fa-solid fa-arrow-down-short-wide", elevasi)
            render_animated_bar("Intensitas Curah Hujan", "fa-solid fa-cloud-showers-heavy", hujan)
        with c2:
            render_animated_bar("Jarak Sungai", "fa-solid fa-water", sungai)
            render_animated_bar("Jenis Tanah", "fa-solid fa-layer-group", tanah)
            
        st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px dashed #E5E7EB;'>", unsafe_allow_html=True)
        
        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown("""
            <div style='margin-bottom: 12px; font-family: Inter, sans-serif; font-size: 13px; font-weight: 600; color: #2B2A28; text-transform: uppercase; letter-spacing: 1px;'>
                <i class='fa-solid fa-users-viewfinder'></i> Komponen Exposure (Keterpaparan)
            </div>
            """, unsafe_allow_html=True)
            render_animated_bar("Kepadatan Penduduk", "fa-solid fa-users-between-lines", populasi)
            render_animated_bar("Kepadatan Bangunan", "fa-solid fa-city", bangunan)
        with c4:
            st.markdown("""
            <div style='margin-bottom: 12px; font-family: Inter, sans-serif; font-size: 13px; font-weight: 600; color: #2B2A28; text-transform: uppercase; letter-spacing: 1px;'>
                <i class='fa-solid fa-house-crack'></i> Komponen Vulnerability (Kerentanan)
            </div>
            """, unsafe_allow_html=True)
            render_animated_bar("Fasilitas Kritis", "fa-solid fa-hospital", fasum)
            
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            w_h = cfg['weights']['hazard']
            w_e = cfg['weights']['exposure']
            w_v = cfg['weights']['vulnerability']
            
            h_val = float(elevasi * w_h['elevasi'] + sungai * w_h['sungai'] + hujan * w_h['hujan'] + tanah * w_h['tanah'])
            e_val = float(populasi * w_e['populasi'] + bangunan * w_e['bangunan'])
            v_val = float(fasum * w_v['fasum'])
            
            w_smce = cfg['weights']['smce']
            t_h = h_val * w_smce['hazard']
            t_e = e_val * w_smce['exposure']
            t_v = v_val * w_smce['vulnerability']
            t_sum = t_h + t_e + t_v
            
            pct_h = (t_h / t_sum * 100) if t_sum else 0
            pct_e = (t_e / t_sum * 100) if t_sum else 0
            pct_v = (t_v / t_sum * 100) if t_sum else 0
            
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=[h_val, e_val, v_val, h_val], 
                theta=['Hazard', 'Exposure', 'Vulnerability', 'Hazard'],
                fill='toself', line_color='#3E6E75', fillcolor='rgba(62, 110, 117, 0.25)'
            ))
            fig_radar.update_layout(
                title=dict(text="Komponen Risiko", font=dict(family='Inter', size=16, color='#111827')),
                polar=dict(
                    radialaxis=dict(visible=True, range=[1, 5], gridcolor="#E5E7EB", tickfont=dict(color='#9CA3AF', family='Inter')), 
                    angularaxis=dict(gridcolor="#E5E7EB", tickfont=dict(color='#6B7280', size=13, family='Inter')),
                    bgcolor="rgba(0,0,0,0)"
                ), 
                showlegend=False, height=300, margin=dict(l=40, r=40, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})
        with c2:
            st.markdown(f"""
<div class='panel-card'>
<div class='panel-title' style='margin-bottom: 12px;'>Kontribusi Faktor Risiko</div>
<div>
<p style='color:#6B7280; margin-bottom:2px; font-size:11px; font-family: Inter, sans-serif; text-transform: uppercase; font-weight: 600;'>HAZARD (Bahaya)</p>
<div style='margin:0; color:#111827; margin-bottom: 12px; font-family: Inter, sans-serif; font-size: 20px; font-weight: 700;'>{pct_h:.1f}%</div>
<p style='color:#6B7280; margin-bottom:2px; font-size:11px; font-family: Inter, sans-serif; text-transform: uppercase; font-weight: 600;'>EXPOSURE (Keterpaparan)</p>
<div style='margin:0; color:#111827; margin-bottom: 12px; font-family: Inter, sans-serif; font-size: 20px; font-weight: 700;'>{pct_e:.1f}%</div>
<p style='color:#6B7280; margin-bottom:2px; font-size:11px; font-family: Inter, sans-serif; text-transform: uppercase; font-weight: 600;'>VULNERABILITY (Kerentanan)</p>
<div style='margin:0; color:#111827; font-family: Inter, sans-serif; font-size: 20px; font-weight: 700;'>{pct_v:.1f}%</div>
</div>
</div>
""", unsafe_allow_html=True)
            
            
    # Tab 4 dihilangkan
        


@st.cache_data
def get_base64_image(img_path):
    if not img_path or not os.path.exists(img_path): return None
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def create_base_map(_boundary_wgs):
    center = get_map_center(_boundary_wgs)
    m = folium.Map(location=[-7.36179,112.72734], zoom_start=12, tiles='OpenStreetMap')
    
    layers = [
        ("Peta Risiko Final", final_tif, True),
        ("Peta Hazard", os.path.join(interim_dir, 'hazard_final.tif'), False),
        ("Peta Exposure", os.path.join(interim_dir, 'exposure_final.tif'), False),
        ("Peta Vulnerability", os.path.join(interim_dir, 'vulnerability_final.tif'), False)
    ]
    
    for name, path, show in layers:
        img_path, overlay_bounds = generate_colormap_image(path)
        encoded = get_base64_image(img_path)
        if encoded:
            folium.raster_layers.ImageOverlay(
                image=f"data:image/png;base64,{encoded}", bounds=overlay_bounds,
                opacity=0.7, name=name, show=show
            ).add_to(m)
    
    

    # Draw boundary vector
    name_col = get_name_column(_boundary_wgs)
    tooltip = None
    if name_col:
        tooltip = folium.GeoJsonTooltip(
            fields=[name_col],
            aliases=[''],
            labels=False,
            className='district-tooltip'
        )

    style_dict = {'fill': True, 'fillColor': 'white', 'fillOpacity': 0.02, 'color': '#2B2A28', 'weight': 1, 'opacity': 0.5}
    folium.GeoJson(
        _boundary_wgs,
        style_function=lambda x: style_dict,
        tooltip=tooltip,
        name="Batas Wilayah"
    ).add_to(m)
    
    # Add District name labels at centroids
    name_col = get_name_column(_boundary_wgs)
    if name_col:
        for _, row in _boundary_wgs.iterrows():
            centroid = row.geometry.centroid
            name = str(row[name_col]).title()
            folium.map.Marker(
                [centroid.y, centroid.x],
                icon=folium.features.DivIcon(
                    icon_size=(150, 30),
                    icon_anchor=(75, 15),
                    html=f"""<div style="font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; color: #2B2B2B; text-align: center; white-space: nowrap; letter-spacing: 0.4px; text-shadow: -1px -1px 0 #FFFFFF, 1px -1px 0 #FFFFFF, -1px 1px 0 #FFFFFF, 1px 1px 0 #FFFFFF; pointer-events: none;">{name}</div>"""
                )
            ).add_to(m)
            
    legend_html = '''
     <div style="position: absolute; bottom: 30px; left: 30px; width: 150px; 
                 background: #FBF9F4;
                 border:1px solid #DDD6C7; z-index:9999; font-size:12px;
                 border-radius: 6px; padding: 14px; color: #2B2A28;">
     <b style="color:#2B2A28; margin-bottom: 10px; display:block; font-family:'IBM Plex Mono', monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;"><i class="fa-solid fa-list"></i> LEGENDA</b>
     <div style="display:flex; align-items:center; margin-bottom:7px; font-size: 11px;"><i style="background:#16A34A; width:12px; height:12px; border-radius:2px; margin-right:10px;"></i> Risiko Rendah</div>
     <div style="display:flex; align-items:center; margin-bottom:7px; font-size: 11px;"><i style="background:#F59E0B; width:12px; height:12px; border-radius:2px; margin-right:10px;"></i> Risiko Sedang</div>
     <div style="display:flex; align-items:center; font-size: 11px;"><i style="background:#DC2626; width:12px; height:12px; border-radius:2px; margin-right:10px;"></i> Risiko Tinggi</div>
     </div>
     <style>
     @import url('https://fonts.googleapis.com/css2?family=Spectral:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
     html, body { margin: 0 !important; padding: 0 !important; height: 100% !important; width: 100% !important; overflow: hidden !important; }
     .folium-map { height: 100% !important; width: 100% !important; position: absolute !important; top: 0 !important; left: 0 !important; bottom: 0 !important; right: 0 !important; }
     
     /* Prevent ImageOverlays and Label Markers from blocking pointer events */
     img.leaflet-image-layer, .leaflet-overlay-pane img { pointer-events: none !important; }
     .leaflet-marker-pane .leaflet-marker-icon { pointer-events: none !important; }
     
     /* Hide st_folium auto-generated selection bounding boxes */
     path[fill="none"], path[fill-opacity="0"] { display: none !important; stroke-width: 0 !important; stroke: transparent !important; }
     
     .district-tooltip {
         background-color: #FFFFFF !important;
         border: 1px solid #E5E7EB !important;
         border-radius: 8px !important;
         padding: 6px 12px !important;
         font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
         font-weight: 600 !important;
         font-size: 13px !important;
         color: #1F2937 !important;
         box-shadow: 0 4px 12px rgba(0,0,0,.12) !important;
         white-space: nowrap !important;
         transition: opacity 150ms ease-in-out !important;
         opacity: 1 !important;
     }
     /* Direction-aware offsets to push tooltip away from cursor */
     .district-tooltip.leaflet-tooltip-top { margin-top: -14px !important; }
     .district-tooltip.leaflet-tooltip-bottom { margin-top: 14px !important; }
     .district-tooltip.leaflet-tooltip-left { margin-left: -14px !important; }
     .district-tooltip.leaflet-tooltip-right { margin-left: 14px !important; }
     .district-tooltip::before, .district-tooltip::after { display: none !important; }
     .leaflet-control-geocoder { position: fixed !important; left: 50% !important; transform: translateX(-50%) !important; top: 8px !important; z-index: 1000 !important; border-radius: 6px !important; border: 1px solid #DDD6C7 !important; box-shadow: none !important; }
     .leaflet-control-geocoder-form input { height: 34px !important; padding: 0 15px !important; font-size: 13px !important; width: 200px !important; margin: 0 !important; font-family: 'IBM Plex Sans', sans-serif; border: none !important; border-radius: 6px !important; outline: none !important; }
     .leaflet-control-geocoder-icon { width: 34px !important; height: 34px !important; border-radius: 6px !important; }
     .leaflet-control-layers-toggle { width: 36px !important; height: 36px !important; background-size: 18px 18px !important; }
     .leaflet-control-layers { font-size: 12px !important; padding: 6px !important; font-family: 'IBM Plex Sans', sans-serif; }
     .leaflet-control-zoom a { width: 32px !important; height: 32px !important; line-height: 30px !important; font-size: 16px !important; }
     </style>
     <script>
      setTimeout(function() {
          var mapInstance = null;
          for (var key in window) {
              if (window[key] && window[key] instanceof L.Map) {
                  mapInstance = window[key];
                  break;
              }
          }
          if (mapInstance) {
              // Debugging selection layer as requested
              mapInstance.on('layeradd', function(e) {
                  // Only log if it's a path and not a CircleMarker to avoid spamming tiles
                  if (typeof L !== 'undefined' && e.layer instanceof L.Path && !(e.layer instanceof L.CircleMarker)) {
                      console.log("NEW LAYER ADDED:", e.layer);
                      console.log("OPTIONS:", e.layer.options);
                  }
              });

              mapInstance.on('mousemove', function(e) {
                  if (window.parent && window.parent.document) {
                      var coordEl = window.parent.document.getElementById('footer-coord');
                      if (coordEl) coordEl.innerText = e.latlng.lat.toFixed(5) + ", " + e.latlng.lng.toFixed(5);
                  }
              });
              mapInstance.on('tooltipopen', function(e) {
                  if (e.tooltip && e.tooltip._content && window.parent && window.parent.document) {
                      var kecEl = window.parent.document.getElementById('footer-kec');
                      if (kecEl) {
                          var div = document.createElement('div');
                          div.innerHTML = e.tooltip._content;
                          kecEl.innerText = div.innerText.trim() || div.textContent.trim();
                      }
                  }
              });
              mapInstance.on('tooltipclose', function(e) {
                  if (window.parent && window.parent.document) {
                      var kecEl = window.parent.document.getElementById('footer-kec');
                      if (kecEl) kecEl.innerText = "-";
                  }
              });
          }
      }, 500);
     </script>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl(position='topleft').add_to(m)
    return m

def main():
    boundary_wgs, boundary_utm = get_boundary_data()
    zonal_results = compute_zonal_stats()
    pop_dict = compute_district_population()
    
    st.markdown("""
        <style>
            .st-emotion-cache-1jicfl2 { padding: 0 !important; }
            div[data-testid="stVerticalBlock"] > div { margin-bottom: 0 !important; gap: 0 !important; }
            .panel-toggle-btn {
                position: fixed;
                top: 32px;
                right: 30px;
                background-color: #FBF9F4;
                color: #2B2A28;
                padding: 10px 16px;
                border-radius: 6px;
                font-family: 'IBM Plex Mono', monospace;
                font-weight: 600;
                font-size: 11px;
                cursor: pointer;
                z-index: 1000000;
                border: 1px solid #DDD6C7;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .panel-toggle-btn:hover {
                border-color: #8A8375;
                transform: translateY(-1px);
            }
            .floating-panel {
                position: fixed;
                top: 106px;
                right: 30px;
                width: 280px;
                max-height: calc(100vh - 148px);
                overflow-y: auto;
                z-index: 999999;
                scrollbar-width: thin;
                opacity: 0;
                visibility: hidden;
                transform: translateX(20px);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            #panel-toggle:checked ~ .floating-panel {
                opacity: 1;
                visibility: visible;
                transform: translateX(0);
            }
            #panel-toggle:checked ~ .panel-toggle-btn {
                background-color: #FBF9F4;
                border-color: #3E6E75;
                color: #3E6E75;
            }
            .floating-panel::-webkit-scrollbar {
                width: 5px;
            }
            .floating-panel::-webkit-scrollbar-thumb {
                background: #DDD6C7;
                border-radius: 3px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    m = create_base_map(boundary_wgs)
    st_data = st_folium(m, use_container_width=True, height=1200, returned_objects=["last_clicked"])
    
    avg_score = sum([r['Skor'] for r in zonal_results]) / len(zonal_results) if zonal_results else 0
    risk_level = "TINGGI" if avg_score >= 3.5 else "SEDANG" if avg_score >= 2.5 else "RENDAH"
    risk_color = "#DC2626" if risk_level == "TINGGI" else "#F59E0B" if risk_level == "SEDANG" else "#16A34A"
    
    html = f"""
    <input type="checkbox" id="panel-toggle" style="display:none;">
    <label for="panel-toggle" class="panel-toggle-btn">
        <i class="fa-solid fa-bars"></i> Ringkasan & Peringkat
    </label>
    <div class="floating-panel">
        <div style="background: #FBF9F4; border: 1px solid #DDD6C7; border-radius: 6px; padding: 12px; margin-bottom: 10px;">
            <div style="font-family: 'IBM Plex Mono', monospace; color: #8A8375; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;"><i class="fa-solid fa-chart-pie"></i> Ringkasan Risiko Banjir</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 20px; font-weight: 700; color: {risk_color}; margin-top: 4px;">RISIKO {risk_level}</div>
            <div style="font-size: 11px; color: #8A8375;">Rata-rata seluruh kota</div>
        </div>
        <div style="background: #FBF9F4; border: 1px solid #DDD6C7; border-radius: 6px; padding: 12px;">
            <div style='font-family: Spectral, serif; color: #2B2A28; font-weight: 700; font-size: 14px; margin-bottom: 10px;'><i class='fa-solid fa-list-ol'></i> Peringkat Risiko</div>
            <div class='ranking-container' style='padding-right: 5px;'>
    """
    
    for i, row in enumerate(zonal_results):
        score = row['Skor']
        pct = (score / 5.0) * 100
        
        if score >= 3.5:
            badge = "<span class='badge badge-high'><i class='fa-solid fa-circle-exclamation'></i> TINGGI</span>"
            fill_color = "#DC2626"
        elif score >= 2.5:
            badge = "<span class='badge badge-med'><i class='fa-solid fa-triangle-exclamation'></i> SEDANG</span>"
            fill_color = "#F59E0B"
        else:
            badge = "<span class='badge badge-low'><i class='fa-solid fa-shield-check'></i> RENDAH</span>"
            fill_color = "#16A34A"
            
        html += f"""<div class='district-card'>
<div class='dc-header'>
    <span class='dc-name'>#{i+1} {row['Kecamatan']}</span>
    {badge}
</div>
<div class='dc-score'>{score:.2f} <span class='dc-score-label'>Skor</span></div>
<div class='mini-bar-bg'><div class='mini-bar-fill' style='width: {pct}%; background: {fill_color};'></div></div>
</div>"""
    
    html += "</div></div></div>"
    st.markdown(html, unsafe_allow_html=True)
        

    if 'last_clicked_coord' not in st.session_state:
        st.session_state.last_clicked_coord = None
        
    if st_data and st_data.get('last_clicked'):
        clicked = st_data['last_clicked']
        coord_str = f"{clicked['lat']:.5f},{clicked['lng']:.5f}"
        
        if st.session_state.last_clicked_coord != coord_str:
            st.session_state.last_clicked_coord = coord_str
            show_detail_popup(clicked['lat'], clicked['lng'], boundary_utm, pop_dict)
            
    coord_text = "Menunggu klik..."
    dist_text = "-"
    if st_data and st_data.get('last_clicked'):
        c_lat, c_lon = st_data['last_clicked']['lat'], st_data['last_clicked']['lng']
        coord_text = f"{c_lat:.5f}, {c_lon:.5f}"
        dist_text = get_district_name(c_lat, c_lon, boundary_utm)

    st.markdown(f"""
        <div style="position: fixed; bottom: 0; left: 0; right: 0; background: #FBF9F4; border-top: 1px solid #DDD6C7; z-index: 99999; padding: 10px 30px; display: flex; justify-content: space-between; font-size: 11px; color: #8A8375; font-family: 'IBM Plex Mono', monospace;">
            <div><i class="fa-solid fa-location-crosshairs"></i> Koordinat: <b style="color:#2B2A28;" id="footer-coord">{coord_text}</b> &nbsp;|&nbsp; <i class="fa-solid fa-map-pin"></i> Kecamatan: <b style="color:#2B2A28;" id="footer-kec">{dist_text}</b></div>
            <div><i class="fa-solid fa-layer-group"></i> Basemap: <b style="color:#2B2A28;">OpenStreetMap</b> &nbsp;|&nbsp; <i class="fa-solid fa-ruler"></i> Skala: <b style="color:#2B2A28;">Dinamis</b></div>
        </div>
    """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
