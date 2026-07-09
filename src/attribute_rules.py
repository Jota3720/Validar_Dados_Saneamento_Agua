from __future__ import annotations

import pandas as pd

from src.issue_schema import make_issue, normalize_issues


def validate_required_attributes(
    df: pd.DataFrame,
    model_group: str,
    *,
    domain: str = "SANEAMENTO",
    code_prefix: str = "SAN",
    run_id: str = "",
) -> pd.DataFrame:
    issues = []
    for _, row in df.iterrows():
        if pd.isna(row.get("source_id")):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_ATT_001",
                    message="ID nulo",
                    domain=domain,
                    theme="ATRIBUTOS",
                    severity="ALTA",
                    source_layer=row.get("source_layer"),
                    source_id=None,
                    model_group=row.get("model_group", model_group),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Preencher IPID/identificador antes de validar relações ou exportar para modelação.",
                    geometry_wkt=row.get("geometry_wkt"),
                    run_id=run_id,
                )
            )
        if model_group.upper() == "LINK" and pd.isna(row.get("diameter_mm")):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_ATT_005",
                    message="Diâmetro em falta",
                    domain=domain,
                    theme="ATRIBUTOS",
                    severity="ALTA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group", model_group),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Preencher diâmetro nominal em mm ou mapear correctamente o campo de origem.",
                    geometry_wkt=row.get("geometry_wkt"),
                    run_id=run_id,
                )
            )
    return normalize_issues(pd.DataFrame(issues), domain=domain, run_id=run_id, default_theme="ATRIBUTOS")
