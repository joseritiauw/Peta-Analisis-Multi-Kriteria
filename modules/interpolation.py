import os
import yaml
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from scipy.spatial import cKDTree
import pyproj

def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def simple_idw(x, y, z, xi, yi, power=2):
    xi_flat, yi_flat = xi.flatten(), yi.flatten()
    tree = cKDTree(np.c_[x, y])
    # Ambil 10 titik terdekat untuk IDW (sesuai literatur)
    dists, idxs = tree.query(np.c_[xi_flat, yi_flat], k=10)
    dists = np.where(dists == 0, 1e-10, dists) # cegah division by zero
    weights = 1.0 / (dists ** power)
    z_interp = np.sum(weights * z[idxs], axis=1) / np.sum(weights, axis=1)
    return z_interp.reshape(xi.shape)

def main():
    print("Loading config...")
    cfg = load_config()
    crs, nodata = cfg['project']['crs'], float(cfg['project']['nodata'])
    raw_dir, interim_dir = cfg['paths']['raw_data'], cfg['paths']['interim']
    
    hujan_path = os.path.join(raw_dir, cfg['files']['hujan'])
    if not os.path.exists(hujan_path):
        print(f"File {hujan_path} tidak ditemukan.")
        return
        
    ref_grid = np.load(os.path.join(interim_dir, 'reference_grid.npz'))
    ref_transform = rasterio.transform.Affine(*ref_grid['transform'])
    ref_width, ref_height = int(ref_grid['width']), int(ref_grid['height'])
    
    print("Membaca titik-titik sampel dari file 1KB...")
    with rasterio.open(hujan_path) as src:
        hujan_data = src.read(1)
        valid_mask = (hujan_data != src.nodata) & (hujan_data > 0)
        rows, cols = np.where(valid_mask)
        z = hujan_data[rows, cols]
        
        x, y = [], []
        for r, c in zip(rows, cols):
            px, py = rasterio.transform.xy(src.transform, r, c, offset='center')
            x.append(px)
            y.append(py)
            
    transformer = pyproj.Transformer.from_crs(src.crs, crs, always_xy=True)
    x_utm, y_utm = transformer.transform(np.array(x), np.array(y))
    
    print(f"Ditemukan {len(z)} titik sampel hujan. Melakukan interpolasi IDW ke grid 30m...")
    col_indices, row_indices = np.meshgrid(np.arange(ref_width), np.arange(ref_height))
    xi, yi = rasterio.transform.xy(ref_transform, row_indices, col_indices, offset='center')
    
    z_interp = simple_idw(x_utm, y_utm, z, np.array(xi), np.array(yi), power=2)
    z_interp = z_interp.reshape((ref_height, ref_width))
    
    print("Menerapkan masking batas kota...")
    boundary = gpd.read_file(os.path.join(raw_dir, cfg['files']['boundary'])).to_crs(crs)
    shapes_bounds = [geom for geom in boundary.geometry]
    mask_out = geometry_mask(shapes_bounds, transform=ref_transform, invert=False, out_shape=(ref_height, ref_width))
    z_interp[mask_out] = nodata
    
    profile = {
        'driver': 'GTiff', 'dtype': 'float32', 'nodata': nodata,
        'width': ref_width, 'height': ref_height, 'count': 1,
        'crs': crs, 'transform': ref_transform, 'compress': 'lzw'
    }
    out_path = os.path.join(interim_dir, 'hujan_30m.tif')
    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(z_interp.astype(np.float32), 1)
        
    print("Interpolasi Curah Hujan Selesai!")

if __name__ == '__main__':
    main()
