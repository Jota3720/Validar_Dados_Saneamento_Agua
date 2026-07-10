from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

ISSUE_COLUMNS = [
    "run_id",
    "domain",
    "theme",
    "regra_id",
    "severity",
    "source_layer",
    "source_id",
    "related_layer",
    "related_id",
    "tolerancia_m",
    "model_group",
    "entity_type",
    "message",
    "suggested_fix",
    "confidence",
    "falso_positivo_possivel",
    "geometry_wkt",
    "created_at",
]

LEGACY_RENAMES = {
    "tipo_erro": "message",
    "gravidade": "severity",
    "geometry": "geometry_wkt",
    "descricao": "message",
    "acao_sugerida": "suggested_fix",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_issues() -> pd.DataFrame:
    return pd.DataFrame(columns=ISSUE_COLUMNS)


def make_issue(
    *,
    regra_id: str,
    message: str,
    domain: str,
    theme: str = "GERAL",
    severity: str = "MEDIA",
    source_layer: Any = None,
    source_id: Any = None,
    related_layer: Any = None,
    related_id: Any = None,
    tolerancia_m: Any = None,
    model_group: Any = None,
    entity_type: Any = None,
    suggested_fix: str = "",
    confidence: Any = None,
    falso_positivo_possivel: Any = None,
    geometry_wkt: Any = None,
    run_id: str = "",
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "domain": domain,
        "theme": theme,
        "regra_id": regra_id,
        "severity": severity,
        "source_layer": source_layer,
        "source_id": source_id,
        "related_layer": related_layer,
        "related_id": related_id,
        "tolerancia_m": tolerancia_m,
        "model_group": model_group,
        "entity_type": entity_type,
        "message": message,
        "suggested_fix": suggested_fix,
        "confidence": confidence,
        "falso_positivo_possivel": falso_positivo_possivel,
        "geometry_wkt": geometry_wkt,
        "created_at": utc_now_iso(),
    }


def normalize_issues(
    df: pd.DataFrame | None,
    *,
    domain: str,
    run_id: str = "",
    default_theme: str = "GERAL",
    default_severity: str = "MEDIA",
) -> pd.DataFrame:
    if df is None or df.empty:
        return empty_issues()

    out = df.copy()
    out = out.rename(columns={k: v for k, v in LEGACY_RENAMES.items() if k in out.columns})

    defaults = {
        "run_id": run_id,
        "domain": domain,
        "theme": default_theme,
        "severity": default_severity,
        "source_layer": None,
        "source_id": None,
        "related_layer": None,
        "related_id": None,
        "tolerancia_m": None,
        "model_group": None,
        "entity_type": None,
        "message": "",
        "suggested_fix": "",
        "confidence": None,
        "falso_positivo_possivel": None,
        "geometry_wkt": None,
        "created_at": utc_now_iso(),
    }

    for col, value in defaults.items():
        if col not in out.columns:
            out[col] = value

    if "regra_id" not in out.columns:
        out["regra_id"] = "REGRA_NAO_CLASSIFICADA"

    out["domain"] = out["domain"].fillna(domain)
    out["run_id"] = out["run_id"].fillna(run_id)
    out["theme"] = out["theme"].fillna(default_theme)
    out["severity"] = out["severity"].fillna(default_severity)

    return out[ISSUE_COLUMNS]


def append_issues(*frames: pd.DataFrame, domain: str, run_id: str = "") -> pd.DataFrame:
    normalized = [normalize_issues(frame, domain=domain, run_id=run_id) for frame in frames if frame is not None]
    if not normalized:
        return empty_issues()
    combined = pd.concat(normalized, ignore_index=True)
    if combined.empty:
        return empty_issues()
    return combined[ISSUE_COLUMNS]
