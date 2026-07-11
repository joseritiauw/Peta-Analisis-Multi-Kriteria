import os
import yaml
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import rasterize, geometry_mask

def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def reclassify_thresholds(data, nodata, thresholds):
    # Kembalikan ke logic normal, pembersihan outlier dilakukan di tingkat param
    valid_mask = data != nodata
    out_data = np.full(data.shape, nodata, dtype=np.float32)
    
    if not np.any(valid_mask):
        return out_data
        
    valid_data = data[valid_mask]
    scores = np.ones_like(valid_data, dtype=np.float32)
    
    # Sort thresholds by upper_bound ascending
    sorted_thresh = sorted(thresholds, key=lambda x: x[0])
    
    # We evaluate from largest bound down to smallest
    for limit, score in reversed(sorted_thresh):
        scores[valid_data <= limit] = score
        
    out_data[valid_mask] = scores
    return out_data

def process_reclassify(input_path, output_path, cfg, param_name):
    if not os.path.exists(input_path):
        print(f"Skipping {param_name}: File not found ({input_path})")
        return
        
    print(f"Reclassifying {param_name}...")
    with rasterio.open(input_path) as src:
        data = src.read(1)
        nodata = src.nodata
        meta = src.meta.copy()
        
    # --- PREPROCESSING OUTLIER KHUSUS PARAMETER ---
    if param_name == 'elevasi':
        # Hanya singkirkan sentinel 32767 atau error ekstrem. Jangan pakai 100m karena perbukitan barat (Sambikerep) bisa terpotong.
        data = np.where((data < -100) | (data > 30000), nodata, data)
    elif param_name == 'populasi':
        # BUG FIX: Jangan set -99999 jadi nodata, karena akan MEMBOLONGI peta (menghapus piksel dari hasil akhir).
        # Set menjadi 0 (tidak ada penduduk/data) agar tetap dihitung dengan skor 1.
        data = np.where(data == -99999, 0, data)
    # ---------------------------------------------
        
    thresholds = cfg['reclassify']['thresholds'].get(param_name)
    if not thresholds:
        print(f"ERROR: Thresholds for {param_name} not found in config.yaml")
        return
        
    out_data = reclassify_thresholds(data, nodata, thresholds)
        
    meta.update(dtype=rasterio.float32)
    with rasterio.open(output_path, 'w', **meta) as dst:
        dst.write(out_data.astype(np.float32), 1)

def process_soil(input_path, output_path, cfg):
    print("Reclassifying tanah (Vector to Raster)...")
    if not os.path.exists(input_path): 
        print("Skipping tanah: File not found")
        return
        
    interim_dir = cfg['paths']['interim']
    ref_grid = np.load(os.path.join(interim_dir, 'reference_grid.npz'))
    ref_transform = rasterio.transform.Affine(*ref_grid['transform'])
    ref_width, ref_height = int(ref_grid['width']), int(ref_grid['height'])
    nodata = float(cfg['project']['nodata'])
    
    gdf = gpd.read_file(input_path)
    lookup = cfg['tanah_lookup']
    
    shapes = []
    for _, row in gdf.iterrows():
        soil_code = row.iloc[0] 
        score = lookup.get(soil_code, 3) 
        shapes.append((row.geometry, score))
        
    if not shapes:
        out_data = np.full((ref_height, ref_width), nodata, dtype=np.float32)
    else:
        out_data = rasterize(shapes, out_shape=(ref_height, ref_width), transform=ref_transform, fill=nodata, dtype=np.float32)
        
    raw_dir = cfg['paths']['raw_data']
    boundary = gpd.read_file(os.path.join(raw_dir, cfg['files']['boundary'])).to_crs(cfg['project']['crs'])
    shapes_bounds = [geom for geom in boundary.geometry]
    mask_out = geometry_mask(shapes_bounds, transform=ref_transform, invert=False, out_shape=(ref_height, ref_width))
    out_data[mask_out] = nodata
    
    profile = {
        'driver': 'GTiff', 'dtype': 'float32', 'nodata': nodata,
        'width': ref_width, 'height': ref_height, 'count': 1,
        'crs': cfg['project']['crs'], 'transform': ref_transform, 'compress': 'lzw'
    }
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(out_data, 1)

def main():
    print("Loading config...")
    cfg = load_config()
    interim_dir = cfg['paths']['interim']
    
    params = {
        'elevasi': 'dem_30m.tif',
        'sungai': 'sungai_distance_30m.tif',
        'hujan': 'hujan_30m.tif',
        'populasi': 'populasi_30m.tif',
        'bangunan': 'bangunan_density_30m.tif',
        'fasum': 'fasum_density_30m.tif'
    }
    
    for param_name, filename in params.items():
        in_path = os.path.join(interim_dir, filename)
        out_path = os.path.join(interim_dir, f"{param_name}_reclass.tif")
        process_reclassify(in_path, out_path, cfg, param_name)
        
    # Khusus untuk tanah (karena asalnya vektor)
    tanah_in = os.path.join(interim_dir, 'tanah_clipped.gpkg')
    tanah_out = os.path.join(interim_dir, 'tanah_reclass.tif')
    process_soil(tanah_in, tanah_out, cfg)
    
    print("Reclassify Selesai!")

if __name__ == '__main__':
    main()
