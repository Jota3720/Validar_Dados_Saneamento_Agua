from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.io import write_csv, write_excel

try:
    from shapely import wkt
except Exception:  # pragma: no cover
    wkt = None

FIELD_CANDIDATES: dict[str, list[str]] = {
    "source_id": ["ipid", "id", "objectid", "gid"],
    "diameter_mm": ["diameter_mm", "diametro_mm", "diametro", "diametro__mm", "dn", "dn_mm", "dnom", "d_nominal"],
    "material": ["material", "material_tubagem", "tipo_material"],
    "status": ["estado", "estado_ciclo_vida", "estado_de_ciclo_de_vida", "estado_de_vida", "status"],
    "arruamento": ["arruamento", "rua", "nome_rua", "toponimo", "toponimia"],
    "freguesia_caop_2012": ["freguesia_caop_2012", "freguesia2012", "freguesia_2012"],
    "freguesia_caop_2017": ["freguesia_caop_2017", "freguesia2017", "freguesia_2017", "freguesia"],
    "numero_policia": ["numero_policia", "num_policia", "n_policia", "porta", "n_porta", "numero_porta"],
    "cota_terreno": ["cota_terreno", "cota", "elevation", "altitude"],
    "cota_tampa": ["cota_tampa", "cota_tampao", "cota_tampão"],
    "cota_fundo": ["cota_fundo", "profundidade_fundo"],
}

NORMALIZED_COLUMNS = [
    "domain",
    "source_layer",
    "source_id",
    "model_group",
    "entity_type",
    "diameter_mm",
    "material",
    "status",
    "arruamento",
    "freguesia_caop_2012",
    "freguesia_caop_2017",
    "numero_policia",
    "cota_terreno",
    "cota_tampa",
    "cota_fundo",
    "geometry_wkt",
]

COMMON_FIELDS = NORMALIZED_COLUMNS


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {str(c).lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate and candidate.lower() in cols:
            return cols[candidate.lower()]
    return None


def _series_from_candidates(df: pd.DataFrame, candidates: list[str], default=None) -> pd.Series:
    col = _first_existing(df, candidates)
    if col is None:
        return pd.Series([default] * len(df), index=df.index)
    return df[col]


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def _load_raw_csvs(raw_dir: Path) -> list[pd.DataFrame]:
    frames = []
    for path in sorted(raw_dir.glob("*.csv")):
        df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
        df["_raw_file"] = path.name
        frames.append(df)
    return frames


def normalize_frame(df: pd.DataFrame, model_group: str, *, domain: str = "") -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["domain"] = domain or _series_from_candidates(df, ["domain"], default="")
    out["source_layer"] = _series_from_candidates(df, ["_source_layer", "source_layer"], default="")
    id_field = None
    if "_id_field" in df.columns and df["_id_field"].notna().any():
        id_field = str(df["_id_field"].dropna().iloc[0]).lower()
    id_candidates = ([id_field] if id_field else []) + FIELD_CANDIDATES["source_id"]
    out["source_id"] = _series_from_candidates(df, id_candidates)
    out["model_group"] = _series_from_candidates(df, ["_model_group", "model_group"], default=model_group)
    out["entity_type"] = _series_from_candidates(df, ["_mapping_alias", "entity_type"], default="UNKNOWN")
    out["diameter_mm"] = _to_numeric(_series_from_candidates(df, FIELD_CANDIDATES["diameter_mm"]))
    out["material"] = _series_from_candidates(df, FIELD_CANDIDATES["material"])
    out["status"] = _series_from_candidates(df, FIELD_CANDIDATES["status"])
    out["arruamento"] = _series_from_candidates(df, FIELD_CANDIDATES["arruamento"])
    out["freguesia_caop_2012"] = _series_from_candidates(df, FIELD_CANDIDATES["freguesia_caop_2012"])
    out["freguesia_caop_2017"] = _series_from_candidates(df, FIELD_CANDIDATES["freguesia_caop_2017"])
    out["numero_policia"] = _series_from_candidates(df, FIELD_CANDIDATES["numero_policia"])
    out["cota_terreno"] = _to_numeric(_series_from_candidates(df, FIELD_CANDIDATES["cota_terreno"]))
    out["cota_tampa"] = _to_numeric(_series_from_candidates(df, FIELD_CANDIDATES["cota_tampa"]))
    out["cota_fundo"] = _to_numeric(_series_from_candidates(df, FIELD_CANDIDATES["cota_fundo"]))
    out["geometry_wkt"] = _series_from_candidates(df, ["geometry_wkt", "wkt", "geom_wkt"])
    return out[NORMALIZED_COLUMNS]


def normalize_raw_exports(run_dir: str | Path, *, domain: str) -> pd.DataFrame:
    run_dir = Path(run_dir)
    raw_dir = run_dir / "exports" / "raw"
    norm_dir = run_dir / "exports" / "normalizado"
    reports_dir = run_dir / "relatorios"
    norm_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    frames = _load_raw_csvs(raw_dir)
    normalized_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []

    for df in frames:
        model_group = str(_series_from_candidates(df, ["_model_group"], default="UNKNOWN").iloc[0]) if len(df) else "UNKNOWN"
        norm = normalize_frame(df, model_group, domain=domain)
        normalized_frames.append(norm)
        summary_rows.append(
            {
                "raw_file": str(df.get("_raw_file", pd.Series([""])).iloc[0]) if len(df) else "",
                "source_layer": str(norm["source_layer"].iloc[0]) if len(norm) else "",
                "model_group": str(norm["model_group"].iloc[0]) if len(norm) else model_group,
                "entity_type": str(norm["entity_type"].iloc[0]) if len(norm) else "",
                "records": len(df),
            }
        )

    if normalized_frames:
        normalized = pd.concat(normalized_frames, ignore_index=True)
    else:
        normalized = pd.DataFrame(columns=NORMALIZED_COLUMNS)

    write_csv(normalized, norm_dir / "network_normalized.csv")
    write_excel(normalized, norm_dir / "network_normalized.xlsx")

    for group, name in [("LINK", "links"), ("NODE", "nodes"), ("RAMAL", "ramais"), ("ZONE", "zones")]:
        subset = normalized[normalized["model_group"].astype(str).str.upper() == group]
        write_csv(subset, norm_dir / f"{name}.csv")

    summary = pd.DataFrame(summary_rows)
    write_csv(summary, reports_dir / "normalizacao_resumo.csv")
    write_excel(summary, reports_dir / "normalizacao_resumo.xlsx")
    return normalized


def load_normalized_with_geometry(run_dir: str | Path) -> pd.DataFrame:
    path = Path(run_dir) / "exports" / "normalizado" / "network_normalized.csv"
    if not path.exists():
        return pd.DataFrame(columns=NORMALIZED_COLUMNS + ["geometry"])
    df = pd.read_csv(path)
    if wkt is None:
        df["geometry"] = None
        return df

    def parse(value):
        if pd.isna(value) or not str(value).strip():
            return None
        try:
            return wkt.loads(str(value))
        except Exception:
            return None

    df["geometry"] = df.get("geometry_wkt", pd.Series([None] * len(df))).apply(parse)
    return df
