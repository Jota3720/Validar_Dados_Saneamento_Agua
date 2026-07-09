from __future__ import annotations

import pandas as pd

from src.issue_schema import make_issue, normalize_issues


def _geometry_wkt(geom) -> str | None:
    if geom is None:
        return None
    return getattr(geom, "wkt", None)


def validate_geometry(
    df: pd.DataFrame,
    zero_length_threshold_m: float = 0.05,
    *,
    domain: str = "SANEAMENTO",
    code_prefix: str = "SAN",
    run_id: str = "",
) -> pd.DataFrame:
    issues = []
    for _, row in df.iterrows():
        geom = row.get("geometry")
        if geom is None:
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_GEO_001",
                    message="Geometria nula ou vazia",
                    domain=domain,
                    theme="GEOMETRIA",
                    severity="ALTA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Rever entidade no cadastro e recriar geometria se necessário.",
                    run_id=run_id,
                )
            )
            continue
        if getattr(geom, "is_empty", False):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_GEO_001",
                    message="Geometria nula ou vazia",
                    domain=domain,
                    theme="GEOMETRIA",
                    severity="ALTA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Rever entidade no cadastro e recriar geometria se necessário.",
                    geometry_wkt=_geometry_wkt(geom),
                    run_id=run_id,
                )
            )
        elif not getattr(geom, "is_valid", True):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_GEO_002",
                    message="Geometria inválida",
                    domain=domain,
                    theme="GEOMETRIA",
                    severity="ALTA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Corrigir geometria antes de executar validações topológicas.",
                    geometry_wkt=_geometry_wkt(geom),
                    run_id=run_id,
                )
            )
        elif getattr(geom, "length", None) is not None and getattr(geom, "length", 0.0) < zero_length_threshold_m:
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_GEO_003",
                    message="Linha com comprimento quase zero",
                    domain=domain,
                    theme="GEOMETRIA",
                    severity="MEDIA",
                    source_layer=row.get("source_layer"),
                    source_id=row.get("source_id"),
                    model_group=row.get("model_group"),
                    entity_type=row.get("entity_type"),
                    suggested_fix="Confirmar se é erro de digitalização, duplicado ou entidade residual.",
                    geometry_wkt=_geometry_wkt(geom),
                    run_id=run_id,
                )
            )
    return normalize_issues(pd.DataFrame(issues), domain=domain, run_id=run_id, default_theme="GEOMETRIA")
