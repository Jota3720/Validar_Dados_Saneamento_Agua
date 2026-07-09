from __future__ import annotations

import pandas as pd


COMMON_FIELDS = [
    "source_layer",
    "source_id",
    "entity_type",
    "model_group",
    "status",
    "arruamento",
    "freguesia_caop_2012",
    "freguesia_caop_2017",
    "numero_policia",
    "diameter_mm",
    "material",
    "length_m",
    "system_type",
    "include_in_model",
    "geometry_wkt",
]


def normalize_frame(df: pd.DataFrame, model_group: str) -> pd.DataFrame:
    out = df.copy()
    if "model_group" not in out:
        out["model_group"] = model_group
    for field in COMMON_FIELDS:
        if field not in out:
            out[field] = None
    return out[COMMON_FIELDS + [c for c in out.columns if c not in COMMON_FIELDS]]
