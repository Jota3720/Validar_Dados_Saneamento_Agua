from __future__ import annotations

import pandas as pd

from src.issue_schema import make_issue, normalize_issues

UNKNOWN_VALUES = {"", "SN", "S/N", "NA", "N/A", "NAO CONHECIDO", "NÃO CONHECIDO", "-- NÃO CONHECIDO --", "-- NAO CONHECIDO --"}


def _is_unknown(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().upper() in UNKNOWN_VALUES


def _is_ramal(row: pd.Series) -> bool:
    text = " ".join(str(row.get(k, "")) for k in ("model_group", "entity_type", "source_layer")).lower()
    return "ramal" in text


def validate_location_metadata(
    df: pd.DataFrame,
    *,
    domain: str = "SANEAMENTO",
    code_prefix: str = "SAN",
    run_id: str = "",
) -> pd.DataFrame:
    issues = []
    for _, row in df.iterrows():
        if _is_unknown(row.get("arruamento")):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_META_ARRUAMENTO",
                    message="Arruamento em falta ou desconhecido",
                    domain=domain,
                    theme="METADADOS",
                    severity="MEDIA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Preencher arruamento ou validar herança espacial por eixo/toponímia.",
                    geometry_wkt=row.get("geometry_wkt"),
                    run_id=run_id,
                )
            )
        if _is_unknown(row.get("freguesia_caop_2012")):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_META_FREG_2012",
                    message="Freguesia CAOP 2012 em falta",
                    domain=domain,
                    theme="METADADOS",
                    severity="BAIXA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Preencher por intersecção espacial com CAOP histórica se ainda for necessária.",
                    geometry_wkt=row.get("geometry_wkt"),
                    run_id=run_id,
                )
            )
        if _is_unknown(row.get("freguesia_caop_2017")):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_META_FREG_2017",
                    message="Freguesia CAOP 2017 em falta",
                    domain=domain,
                    theme="METADADOS",
                    severity="BAIXA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Preencher por intersecção espacial com CAOP.",
                    geometry_wkt=row.get("geometry_wkt"),
                    run_id=run_id,
                )
            )
        if _is_ramal(row) and _is_unknown(row.get("numero_policia")):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_META_NUM_POL",
                    message="Número de polícia em falta ou desconhecido",
                    domain=domain,
                    theme="METADADOS",
                    severity="MEDIA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Confirmar ligação do ramal ao edifício/artigo e preencher número de polícia.",
                    geometry_wkt=row.get("geometry_wkt"),
                    run_id=run_id,
                )
            )
    return normalize_issues(pd.DataFrame(issues), domain=domain, run_id=run_id, default_theme="METADADOS")
