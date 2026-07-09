from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None


def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = ensure_parent(path)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def write_excel(df: pd.DataFrame, path: str | Path, sheet_name: str = "Sheet1") -> None:
    p = ensure_parent(path)
    with pd.ExcelWriter(p, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


def write_gdf(gdf, path: str | Path) -> None:
    if gpd is None:
        raise RuntimeError("geopandas is not available")
    p = ensure_parent(path)
    gdf.to_file(p, driver="GPKG")
