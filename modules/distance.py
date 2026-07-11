import os
import yaml
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize, geometry_mask
from scipy.ndimage import distance_transform_edt

def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def main():
    print("Loading config...")
    cfg = load_config()
    crs, res, nodata = cfg['project']['crs'], cfg['project']['resolution'], float(cfg['project']['nodata'])
    raw_dir, interim_dir = cfg['paths']['raw_data'], cfg['paths']['interim']
    
    ref_grid = np.load(os.path.join(interim_dir, 'reference_grid.npz'))
    ref_transform = rasterio.transform.Affine(*ref_grid['transform'])
    ref_width, ref_height = int(ref_grid['width']), int(ref_grid['height'])
    
    print("Membaca data sungai...")
    sungai = gpd.read_file(os.path.join(interim_dir, 'sungai_clipped.gpkg'))
    
    print("Rasterisasi sungai ke grid 30m...")
    shapes = [(geom, 1) for geom in sungai.geometry]
    if not shapes:
        mask = np.zeros((ref_height, ref_width), dtype=np.uint8)
    else:
        mask = rasterize(shapes, out_shape=(ref_height, ref_width), transform=ref_transform, fill=0, all_touched=True, dtype=np.uint8)
    
    print("Menghitung Euclidean Distance (EDT)...")
    inv_mask = 1 - mask
    distance = distance_transform_edt(inv_mask, sampling=[res, res])
    
    print("Menerapkan masking batas kota...")
    boundary = gpd.read_file(os.path.join(raw_dir, cfg['files']['boundary'])).to_crs(crs)
    shapes_bounds = [geom for geom in boundary.geometry]
    mask_out = geometry_mask(shapes_bounds, transform=ref_transform, invert=False, out_shape=(ref_height, ref_width))
    distance[mask_out] = nodata
    
    profile = {
        'driver': 'GTiff', 'dtype': 'float32', 'nodata': nodata,
        'width': ref_width, 'height': ref_height, 'count': 1,
        'crs': crs, 'transform': ref_transform, 'compress': 'lzw'
    }
    out_path = os.path.join(interim_dir, 'sungai_distance_30m.tif')
    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(distance.astype(np.float32), 1)
        
    print("Perhitungan Jarak Sungai Selesai!")

if __name__ == '__main__':
    main()
