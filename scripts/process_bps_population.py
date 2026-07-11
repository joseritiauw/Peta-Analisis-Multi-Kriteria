import os
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
import numpy as np

def main():
    print("="*60)
    print(" INTEGRASI DATA POPULASI BPS 2024 KE RASTER 30m ".center(60))
    print("="*60)

    # 1. Baca data batas administrasi
    boundary_path = "data/boundary_surabaya_lvl3.gpkg"
    if not os.path.exists(boundary_path):
        boundary_path = "../data/boundary_surabaya_lvl3.gpkg"
    
    print(f"Membaca batas administrasi: {boundary_path}")
    gdf = gpd.read_file(boundary_path)
    # Ubah CRS ke EPSG:32749 (UTM 49S) untuk menghitung luas dalam meter persegi
    gdf = gdf.to_crs("EPSG:32749")
    
    # 2. Baca data BPS
    bps_path = "data/Jumlah Penduduk Menurut Kewarganegaraan dan Jenis Kelamin per Kecamatan, 2024.csv"
    if not os.path.exists(bps_path):
        bps_path = "../data/Jumlah Penduduk Menurut Kewarganegaraan dan Jenis Kelamin per Kecamatan, 2024.csv"
        
    print(f"Membaca data BPS: {bps_path}")
    # Skip header yang tidak perlu, baca kolom yang relevan (index 0 untuk Kecamatan, index 3 untuk Total WNI)
    # Berdasarkan inspeksi, data sebenarnya mulai dari baris ke-6 (skiprows=5)
    df_bps = pd.read_csv(bps_path, skiprows=5, usecols=[0, 3], names=['Kecamatan', 'Total_WNI'])
    df_bps = df_bps.dropna()
    
    # Bersihkan nama kecamatan untuk pencocokan yang lebih baik
    df_bps['Kecamatan'] = df_bps['Kecamatan'].str.strip().str.upper()
    
    # Asumsikan nama kolom kecamatan di GPKG adalah 'NAME_3'
    kec_col = None
    for col in ['NAME_3', 'NAMOBJ', 'WADMKC', 'KECAMATAN', 'Kecamatan']:
        if col in gdf.columns:
            kec_col = col
            break
            
    if kec_col is None:
        print("ERROR: Tidak dapat menemukan kolom nama kecamatan di batas administrasi.")
        print("Kolom yang tersedia:", gdf.columns.tolist())
        return

    # Bersihkan nama untuk cross-matching
    gdf[kec_col] = gdf[kec_col].str.strip().str.upper()
    # Koreksi nama GADM yang sering salah eja dibanding BPS
    gdf[kec_col] = gdf[kec_col].str.replace('PABEANCANTIAN', 'PABEAN CANTIAN')
    gdf[kec_col] = gdf[kec_col].str.replace('KARANG PILANG', 'KARANGPILANG')
    
    # 3. Gabungkan Data (Spatial Join secara Tabular)
    gdf_joined = gdf.merge(df_bps, left_on=kec_col, right_on='Kecamatan', how='left')
    
    # 4. Hitung Kepadatan Penduduk (Jiwa / Km2)
    # Area dalam m2 / 1.000.000 = Area dalam Km2
    gdf_joined['Area_Km2'] = gdf_joined.geometry.area / 1_000_000
    gdf_joined['Kepadatan'] = gdf_joined['Total_WNI'] / gdf_joined['Area_Km2']
    
    # Fill NaN dengan 0 untuk area yang tidak memiliki data (jika ada)
    gdf_joined['Kepadatan'] = gdf_joined['Kepadatan'].fillna(0)
    
    print("\nSampel Kepadatan (Jiwa/Km²):")
    print(gdf_joined[['Kecamatan', 'Total_WNI', 'Area_Km2', 'Kepadatan']].head())

    # 5. Rasterisasi menggunakan referensi DEM
    ref_raster_path = "data/interim/dem_30m.tif"
    if not os.path.exists(ref_raster_path):
        ref_raster_path = "../data/interim/dem_30m.tif"
        
    print(f"\nMembaca raster referensi: {ref_raster_path}")
    with rasterio.open(ref_raster_path) as src:
        meta = src.meta.copy()
        ref_transform = src.transform
        ref_width = src.width
        ref_height = src.height
        nodata = src.nodata
        
    # Siapkan shapes untuk rasterisasi
    shapes = ((geom, value) for geom, value in zip(gdf_joined.geometry, gdf_joined['Kepadatan']))
    
    # Rasterize
    print("Membakar (rasterizing) data kepadatan ke piksel 30m...")
    out_data = rasterize(
        shapes=shapes,
        out_shape=(ref_height, ref_width),
        transform=ref_transform,
        fill=nodata,
        dtype=np.float32
    )
    
    # 6. Simpan output, menimpa file populasi_30m.tif yang lama
    out_path = "data/interim/populasi_30m.tif"
    if not os.path.exists(os.path.dirname(out_path)):
        out_path = "../data/interim/populasi_30m.tif"
        
    meta.update(dtype=rasterio.float32)
    
    print(f"Menyimpan hasil ke: {out_path}")
    with rasterio.open(out_path, 'w', **meta) as dst:
        dst.write(out_data, 1)
        
    print("\nProses integrasi BPS selesai dengan sukses!")
    print("Silakan jalankan ulang 'python modules/reclassify.py' setelah menyesuaikan config.yaml")

if __name__ == '__main__':
    main()
