from __future__ import annotations

import pandas as pd


def _is_ramal(row: pd.Series) -> bool:
    text = " ".join(str(row.get(k, "")) for k in ("model_group", "entity_type", "source_layer")).lower()
    return "ramal" in text


def validate_location_metadata(df: pd.DataFrame) -> pd.DataFrame:
    issues = []
    for _, row in df.iterrows():
        if pd.isna(row.get("arruamento")) or str(row.get("arruamento")).strip().upper() in {"", "SN", "NAO CONHECIDO", "NÃO CONHECIDO"}:
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_META_ARRUAMENTO", "Arruamento em falta ou desconhecido"))
        if pd.isna(row.get("freguesia_caop_2012")):
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_META_FREG_2012", "Freguesia CAOP 2012 em falta"))
        if pd.isna(row.get("freguesia_caop_2017")):
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_META_FREG_2017", "Freguesia CAOP 2017 em falta"))
        if _is_ramal(row) and (pd.isna(row.get("numero_policia")) or str(row.get("numero_policia")).strip().upper() in {"", "SN", "NAO CONHECIDO", "NÃO CONHECIDO"}):
            issues.append((row.get("source_layer"), row.get("source_id"), "SAN_META_NUM_POL", "Numero de policia em falta ou desconhecido"))
    return pd.DataFrame(issues, columns=["source_layer", "source_id", "regra_id", "tipo_erro"])
