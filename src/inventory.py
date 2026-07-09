from __future__ import annotations

import pandas as pd


def build_inventory_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["source_layer", "geometry_type", "srid", "record_count"])
    cols = [c for c in ["source_layer", "geometry_type", "srid", "record_count"] if c in df.columns]
    return df[cols].copy()
