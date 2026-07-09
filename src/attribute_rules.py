from __future__ import annotations

import pandas as pd


def validate_required_attributes(df: pd.DataFrame, model_group: str) -> pd.DataFrame:
    issues = []
    for _, row in df.iterrows():
        if pd.isna(row.get("source_id")):
            issues.append((row.get("source_layer"), None, "SAN_ATT_001", "ID nulo"))
        if model_group == "LINK" and pd.isna(row.get("diameter_mm")):
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_ATT_005", "Diametro em falta"))
    return pd.DataFrame(issues, columns=["source_layer", "source_id", "regra_id", "tipo_erro"])
