import geopandas as gpd
import os
import yaml
from rasterstats import zonal_stats

with open('config.yaml', 'r') as f:
    cfg = yaml.safe_load(f)

raw_dir = cfg['paths']['raw_data']
interim_dir = cfg['paths']['interim']
boundary_path = os.path.join(raw_dir, cfg['files']['boundary'])
pop_path = os.path.join(interim_dir, 'populasi_30m.tif')

boundary = gpd.read_file(boundary_path)
print("Columns:", boundary.columns.tolist())

# Test finding name col
name_col = None
possible_names = ['WADMKC', 'NAMOBJ', 'NAME_3', 'NAME_2', 'KECAMATAN', 'KEC', 'NAMA']
for p in possible_names:
    if p in boundary.columns:
        name_col = p
        break
if not name_col:
    for col in boundary.columns:
        if boundary[col].dtype == 'O' and col != 'geometry' and 'ID' not in col.upper() and 'CODE' not in col.upper():
            name_col = col
            break
print("Selected Name Column:", name_col)
print("Sample Name:", boundary[name_col].iloc[0] if name_col else "None")

# Test Zonal stats
stats = zonal_stats(boundary, pop_path, stats="sum", nodata=cfg['project']['nodata'])
print("First 3 pop sums:", [s['sum'] for s in stats[:3]])
