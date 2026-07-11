import rasterio
import numpy as np

def check(p):
    with rasterio.open(p) as src:
        arr = src.read(1)
        valid = arr[arr != src.nodata]
        if len(valid) > 0:
            print(f"{p}: min={valid.min()}, max={valid.max()}, mean={valid.mean()}")
        else:
            print(f"{p}: ALL NODATA")

check('data/interim/hazard_final.tif')
check('data/interim/exposure_final.tif')
check('data/interim/vulnerability_final.tif')
