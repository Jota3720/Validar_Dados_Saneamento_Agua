from __future__ import annotations

import pandas as pd


def validate_geometry(df: pd.DataFrame, zero_length_threshold_m: float = 0.05) -> pd.DataFrame:
    issues = []
    for _, row in df.iterrows():
        geom = row.get("geometry")
        if geom is None:
            continue
        if getattr(geom, "is_empty", False):
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_GEO_001", "Geometria nula ou vazia"))
        elif not getattr(geom, "is_valid", True):
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_GEO_002", "Geometria invalida"))
        elif getattr(geom, "length", 0.0) is not None and getattr(geom, "length", 0.0) < zero_length_threshold_m:
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_GEO_003", "Linha com comprimento quase zero"))
    return pd.DataFrame(issues, columns=["source_layer", "source_id", "regra_id", "tipo_erro"])
