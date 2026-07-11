import os
import yaml
import numpy as np
import rasterio

def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def read_raster(path):
    with rasterio.open(path) as src:
        return src.read(1), src.nodata, src.meta

def main():
    print("Loading config...")
    cfg = load_config()
    interim_dir = cfg['paths']['interim']
    final_dir = cfg['paths']['final']
    
    paths = {
        'elevasi': os.path.join(interim_dir, 'elevasi_reclass.tif'),
        'sungai': os.path.join(interim_dir, 'sungai_reclass.tif'),
        'hujan': os.path.join(interim_dir, 'hujan_reclass.tif'),
        'tanah': os.path.join(interim_dir, 'tanah_reclass.tif'),
        'populasi': os.path.join(interim_dir, 'populasi_reclass.tif'),
        'bangunan': os.path.join(interim_dir, 'bangunan_reclass.tif'),
        'fasum': os.path.join(interim_dir, 'fasum_reclass.tif')
    }
    
    data = {}
    nodata_val = None
    meta = None
    for key, p in paths.items():
        if not os.path.exists(p):
            print(f"ERROR: File {p} tidak ditemukan. Harap jalankan reclassify.py terlebih dahulu.")
            return
        print(f"Reading {key}...")
        arr, nd, m = read_raster(p)
        data[key] = arr
        if nodata_val is None:
            nodata_val = nd
            meta = m.copy()
            
    print("Membangun Valid Mask (mengecualikan NoData)...")
    valid_mask = np.ones(data['elevasi'].shape, dtype=bool)
    for arr in data.values():
        valid_mask &= (arr != nodata_val)
        
    print("Menghitung Hazard, Exposure, Vulnerability...")
    w_h = cfg['weights']['hazard']
    hazard = (data['elevasi'] * w_h['elevasi'] + 
              data['sungai'] * w_h['sungai'] + 
              data['hujan'] * w_h['hujan'] + 
              data['tanah'] * w_h['tanah'])
              
    w_e = cfg['weights']['exposure']
    exposure = (data['populasi'] * w_e['populasi'] + 
                data['bangunan'] * w_e['bangunan'])
                
    w_v = cfg['weights']['vulnerability']
    vulnerability = data['fasum'] * w_v['fasum']
    
    print("Menyimpan komponen H, E, V secara terpisah...")
    h_save = np.full(hazard.shape, nodata_val, dtype=np.float32)
    h_save[valid_mask] = hazard[valid_mask]
    e_save = np.full(exposure.shape, nodata_val, dtype=np.float32)
    e_save[valid_mask] = exposure[valid_mask]
    v_save = np.full(vulnerability.shape, nodata_val, dtype=np.float32)
    v_save[valid_mask] = vulnerability[valid_mask]
    
    meta_out = meta.copy()
    meta_out.update(dtype=rasterio.float32)
    with rasterio.open(os.path.join(interim_dir, 'hazard_final.tif'), 'w', **meta_out) as dst:
        dst.write(h_save, 1)
    with rasterio.open(os.path.join(interim_dir, 'exposure_final.tif'), 'w', **meta_out) as dst:
        dst.write(e_save, 1)
    with rasterio.open(os.path.join(interim_dir, 'vulnerability_final.tif'), 'w', **meta_out) as dst:
        dst.write(v_save, 1)
    
    print("Melakukan Weighted Linear Combination (WLC)...")
    risk_raw = np.full(data['elevasi'].shape, np.nan, dtype=np.float32)
    
    w_smce = cfg['weights']['smce']
    w_h_smce = w_smce['hazard']
    w_e_smce = w_smce['exposure']
    w_v_smce = w_smce['vulnerability']
    
    risk_raw[valid_mask] = (hazard[valid_mask] * w_h_smce + 
                            exposure[valid_mask] * w_e_smce + 
                            vulnerability[valid_mask] * w_v_smce)
    
    valid_risk = risk_raw[valid_mask]
    min_r = np.nanmin(valid_risk)
    max_r = np.nanmax(valid_risk)
    
    print(f"Nilai Risk Index terendah: {min_r:.3f}, tertinggi: {max_r:.3f}")
    
    print("Membagi Risk Index ke dalam kelas risiko final (1-5)...")
    # Karena input (H,E,V) direclass 1-5, hasil WLC juga otomatis 1-5.
    # Kita bulatkan ke integer terdekat (1-5) untuk klasifikasi risiko akhir
    final_risk = np.full(risk_raw.shape, nodata_val, dtype=np.float32)
    final_risk[valid_mask] = np.round(risk_raw[valid_mask])
    final_risk[valid_mask] = np.clip(final_risk[valid_mask], 1, 5)
    
    print("Menyimpan Peta Risiko Final...")
    meta.update(dtype=rasterio.float32)
    out_path = os.path.join(final_dir, 'peta_risiko_final.tif')
    with rasterio.open(out_path, 'w', **meta) as dst:
        dst.write(final_risk.astype(np.float32), 1)
        
    print("Selesai! Peta Risiko Final tersimpan di:", out_path)

if __name__ == '__main__':
    main()
