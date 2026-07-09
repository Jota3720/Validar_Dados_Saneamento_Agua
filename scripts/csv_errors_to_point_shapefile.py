from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None


def csv_to_shapefile(csv_path: str | Path, out_path: str | Path, geometry_column: str = "geometry_wkt") -> None:
    if gpd is None:
        raise RuntimeError("geopandas is required")
    df = pd.read_csv(csv_path)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkt(df[geometry_column]))
    gdf.to_file(out_path)
