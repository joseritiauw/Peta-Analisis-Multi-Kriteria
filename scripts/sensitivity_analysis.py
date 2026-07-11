import os
import yaml
import numpy as np
import rasterio
import pandas as pd

def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def run_scenario(h_data, e_data, v_data, valid_mask, w_h, w_e, w_v):
    risk = np.zeros_like(h_data, dtype=np.float32)
    risk[valid_mask] = (h_data[valid_mask] * w_h + 
                        e_data[valid_mask] * w_e + 
                        v_data[valid_mask] * w_v)
    
    # Classify 1-5
    final_risk = np.zeros_like(risk, dtype=np.float32)
    final_risk[valid_mask] = np.round(risk[valid_mask])
    final_risk[valid_mask] = np.clip(final_risk[valid_mask], 1, 5)
    
    # Count pixels in each class
    counts = {i: np.sum(final_risk[valid_mask] == i) for i in range(1, 6)}
    return counts

def main():
    print("=== SENSITIVITY ANALYSIS ===")
    # Adjust path if run from scripts folder
    cfg_path = '../config.yaml' if os.path.exists('../config.yaml') else 'config.yaml'
    cfg = load_config(cfg_path)
    
    interim_dir = cfg['paths']['interim']
    if not os.path.exists(interim_dir) and os.path.exists(os.path.join('..', interim_dir)):
        interim_dir = os.path.join('..', interim_dir)
        
    h_path = os.path.join(interim_dir, 'hazard_final.tif')
    e_path = os.path.join(interim_dir, 'exposure_final.tif')
    v_path = os.path.join(interim_dir, 'vulnerability_final.tif')
    
    if not (os.path.exists(h_path) and os.path.exists(e_path) and os.path.exists(v_path)):
        print("ERROR: Komponen H, E, V belum ada. Jalankan run_backend.py terlebih dahulu.")
        return
        
    with rasterio.open(h_path) as src:
        h_data = src.read(1)
        nodata = src.nodata
    with rasterio.open(e_path) as src:
        e_data = src.read(1)
    with rasterio.open(v_path) as src:
        v_data = src.read(1)
        
    valid_mask = (h_data != nodata) & (e_data != nodata) & (v_data != nodata)
    total_pixels = np.sum(valid_mask)
    print(f"Total valid pixels: {total_pixels}")
    
    scenarios = [
        ("Baseline (0.4, 0.35, 0.25)", 0.40, 0.35, 0.25),
        ("Hazard Dominan (0.6, 0.2, 0.2)", 0.60, 0.20, 0.20),
        ("Exposure Dominan (0.2, 0.6, 0.2)", 0.20, 0.60, 0.20),
        ("Vulnerability Dominan (0.2, 0.2, 0.6)", 0.20, 0.20, 0.60),
        ("Equal Weights (0.33, 0.33, 0.33)", 0.333, 0.333, 0.334)
    ]
    
    results = []
    for name, wh, we, wv in scenarios:
        counts = run_scenario(h_data, e_data, v_data, valid_mask, wh, we, wv)
        # Convert to percentages
        pcts = {f"Kelas {k} (%)": (v / total_pixels) * 100 for k, v in counts.items()}
        row = {"Skenario": name, "W_H": wh, "W_E": we, "W_V": wv}
        row.update({k: round(v, 2) for k, v in pcts.items()})
        results.append(row)
        
    df = pd.DataFrame(results)
    
    out_csv = "sensitivity_results.csv"
    if os.path.exists('../config.yaml'):
        out_csv = os.path.join('..', out_csv)
    df.to_csv(out_csv, index=False)
    print(f"\\nHasil Sensitivity Analysis disimpan ke: {out_csv}")
    print(df.to_string())

if __name__ == '__main__':
    main()
