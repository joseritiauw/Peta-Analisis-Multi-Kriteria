import os
import yaml
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import rasterize, geometry_mask
from scipy.ndimage import uniform_filter

def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def create_reference_grid(boundary_gdf, resolution):
    bounds = boundary_gdf.total_bounds
    minx, miny, maxx, maxy = bounds
    width = int(np.ceil((maxx - minx) / resolution))
    height = int(np.ceil((maxy - miny) / resolution))
    transform = rasterio.transform.from_origin(minx, maxy, resolution, resolution)
    return transform, width, height, bounds

def process_raster(input_path, output_path, ref_transform, ref_width, ref_height, boundary_gdf, crs, nodata_val):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return
        
    with rasterio.open(input_path) as src:
        dst_array = np.empty((ref_height, ref_width), dtype=np.float32)
        
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_array,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=crs,
            resampling=Resampling.bilinear
        )
        
        # Apply NoData mask from boundary
        shapes = [geom for geom in boundary_gdf.geometry]
        mask = geometry_mask(shapes, transform=ref_transform, invert=False, out_shape=(ref_height, ref_width))
        dst_array[mask] = nodata_val
        
        profile = {
            'driver': 'GTiff', 'dtype': 'float32', 'nodata': nodata_val,
            'width': ref_width, 'height': ref_height, 'count': 1,
            'crs': crs, 'transform': ref_transform, 'compress': 'lzw'
        }
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(dst_array, 1)
            
def process_bangunan_bcr(input_path, output_path, ref_transform, ref_width, ref_height, boundary_gdf, crs, nodata_val):
    if not os.path.exists(input_path):
        return
    gdf = gpd.read_file(input_path)
    if gdf.crs is None: gdf.set_crs("EPSG:4326", inplace=True)
    gdf = gdf.to_crs(crs)
    gdf = gpd.clip(gdf, boundary_gdf)
    
    shapes = [(geom, 1) for geom in gdf.geometry]
    if not shapes:
        density = np.zeros((ref_height, ref_width), dtype=np.float32)
    else:
        # Rasterize and smooth to approximate building density per 30m
        mask_b = rasterize(shapes, out_shape=(ref_height, ref_width), transform=ref_transform, fill=0, all_touched=True, dtype=np.float32)
        density = uniform_filter(mask_b, size=3)
        
    shapes_bounds = [geom for geom in boundary_gdf.geometry]
    mask_out = geometry_mask(shapes_bounds, transform=ref_transform, invert=False, out_shape=(ref_height, ref_width))
    density[mask_out] = nodata_val
    
    profile = {
        'driver': 'GTiff', 'dtype': 'float32', 'nodata': nodata_val,
        'width': ref_width, 'height': ref_height, 'count': 1,
        'crs': crs, 'transform': ref_transform, 'compress': 'lzw'
    }
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(density, 1)

def process_fasum_kde(input_path, output_path, ref_transform, ref_width, ref_height, boundary_gdf, crs, nodata_val, radius_m=500, res=30):
    if not os.path.exists(input_path):
        return
    gdf = gpd.read_file(input_path)
    if gdf.crs is None: gdf.set_crs("EPSG:4326", inplace=True)
    gdf = gdf.to_crs(crs)
    gdf = gpd.clip(gdf, boundary_gdf)
    
    # Gunakan centroid titik tengah fasilitas
    gdf['geometry'] = gdf.centroid
    x, y = gdf.geometry.x, gdf.geometry.y
    
    minx, maxy = ref_transform.c, ref_transform.f
    maxx, miny = minx + ref_width * res, maxy - ref_height * res
    
    xbins = np.linspace(minx, maxx, ref_width + 1)
    ybins = np.linspace(miny, maxy, ref_height + 1)
    
    hist, _, _ = np.histogram2d(x, y, bins=[xbins, ybins])
    hist = hist.T[::-1] # Flip y-axis
    
    window_size = max(1, int(radius_m / res))
    density = uniform_filter(hist, size=window_size) * (window_size**2)
    
    shapes_bounds = [geom for geom in boundary_gdf.geometry]
    mask_out = geometry_mask(shapes_bounds, transform=ref_transform, invert=False, out_shape=(ref_height, ref_width))
    density[mask_out] = nodata_val
    
    profile = {
        'driver': 'GTiff', 'dtype': 'float32', 'nodata': nodata_val,
        'width': ref_width, 'height': ref_height, 'count': 1,
        'crs': crs, 'transform': ref_transform, 'compress': 'lzw'
    }
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(density.astype(np.float32), 1)

def main():
    print("Loading config...")
    cfg = load_config()
    crs, res, nodata = cfg['project']['crs'], cfg['project']['resolution'], float(cfg['project']['nodata'])
    raw_dir, interim_dir = cfg['paths']['raw_data'], cfg['paths']['interim']
    
    print("Membaca boundary dan menyiapkan Reference Grid...")
    boundary = gpd.read_file(os.path.join(raw_dir, cfg['files']['boundary']))
    if boundary.crs is None: boundary.set_crs("EPSG:4326", inplace=True)
    boundary = boundary.to_crs(crs)
    ref_transform, ref_width, ref_height, bounds = create_reference_grid(boundary, res)
    
    print("Memproses Vektor Dasar (Sungai, Tanah)...")
    import fiona
    sungai_path = os.path.join(raw_dir, cfg['files']['sungai'])
    layers = fiona.listlayers(sungai_path)
    layer_name = next((l for l in layers if 'line' in l.lower()), layers[0])
    sungai = gpd.read_file(sungai_path, layer=layer_name)
    if sungai.crs is None: sungai.set_crs("EPSG:4326", inplace=True)
    sungai = sungai.to_crs(crs)
    gpd.clip(sungai, boundary).to_file(os.path.join(interim_dir, 'sungai_clipped.gpkg'), driver='GPKG')
    
    tanah = gpd.read_file(os.path.join(raw_dir, cfg['files']['tanah']))
    if tanah.crs is None: tanah.set_crs("EPSG:4326", inplace=True)
    tanah = tanah.to_crs(crs)
    tanah = gpd.clip(tanah, boundary)
    tanah.to_file(os.path.join(interim_dir, 'tanah_clipped.gpkg'), driver='GPKG')
    
    print(f"Atribut unik Jenis Tanah yang ditemukan: {tanah.iloc[:, 0].unique()}")
    
    print("Memproses Raster (DEM & Populasi)...")
    process_raster(os.path.join(raw_dir, cfg['files']['dem']), os.path.join(interim_dir, 'dem_30m.tif'), ref_transform, ref_width, ref_height, boundary, crs, nodata)
    process_raster(os.path.join(raw_dir, cfg['files']['populasi']), os.path.join(interim_dir, 'populasi_30m.tif'), ref_transform, ref_width, ref_height, boundary, crs, nodata)
    
    print("Memproses Kepadatan (Exposure & Vulnerability)...")
    process_bangunan_bcr(os.path.join(raw_dir, cfg['files']['bangunan']), os.path.join(interim_dir, 'bangunan_density_30m.tif'), ref_transform, ref_width, ref_height, boundary, crs, nodata)
    process_fasum_kde(os.path.join(raw_dir, cfg['files']['fasum']), os.path.join(interim_dir, 'fasum_density_30m.tif'), ref_transform, ref_width, ref_height, boundary, crs, nodata, cfg['density']['fasum_radius_m'], res)
    
    # Save reference grid params
    np.savez(os.path.join(interim_dir, 'reference_grid.npz'), transform=np.array(ref_transform).astype(float), width=ref_width, height=ref_height, bounds=bounds)
    print("Preprocessing Selesai! Semua data sudah di-align ke grid 30m.")

if __name__ == '__main__':
    main()
