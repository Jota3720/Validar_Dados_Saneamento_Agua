from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from src.attribute_rules import validate_required_attributes
from src.geometry_rules import validate_geometry
from src.io import write_csv, write_excel
from src.issue_schema import append_issues, empty_issues
from src.metadata_rules import validate_location_metadata
from src.normalization import load_normalized_with_geometry
from src.topology_rules import validate_nodes_links

try:
    import geopandas as gpd
    from shapely import wkt
except Exception:  # pragma: no cover
    gpd = None
    wkt = None


def _domain_prefix(domain: str) -> str:
    return "AGUA" if domain.upper() == "AGUA" else "SAN"


def _link_term(domain: str) -> str:
    return "conduta/adutora/ramal de água" if domain.upper() == "AGUA" else "colector/conduta elevatória"


def _read_tolerances(path: str | Path | None) -> dict:
    if not path:
        return {}
    from src.config_loader import load_yaml

    return load_yaml(path)


def _filter_by_group(df: pd.DataFrame, group: str) -> pd.DataFrame:
    if df.empty or "model_group" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["model_group"].astype(str).str.upper() == group.upper()].copy()


def _combine_frames(frames: Iterable[pd.DataFrame], *, domain: str, run_id: str) -> pd.DataFrame:
    result = append_issues(*list(frames), domain=domain, run_id=run_id)
    if result.empty:
        return empty_issues()
    severity_order = {"CRITICA": 0, "CRÍTICA": 0, "ALTA": 1, "MEDIA": 2, "MÉDIA": 2, "BAIXA": 3}
    result["_severity_order"] = result["severity"].astype(str).str.upper().map(severity_order).fillna(9)
    result = result.sort_values(["_severity_order", "theme", "regra_id", "source_layer", "source_id"]).drop(columns=["_severity_order"])
    return result.reset_index(drop=True)


def _make_readable(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(
            columns=[
                "gravidade",
                "tema",
                "regra",
                "camada",
                "id_entidade",
                "grupo_modelo",
                "tipo_entidade",
                "erro",
                "correcao_sugerida",
                "geometria_wkt",
            ]
        )
    return pd.DataFrame(
        {
            "gravidade": issues["severity"],
            "tema": issues["theme"],
            "regra": issues["regra_id"],
            "camada": issues["source_layer"],
            "id_entidade": issues["source_id"],
            "grupo_modelo": issues["model_group"],
            "tipo_entidade": issues["entity_type"],
            "erro": issues["message"],
            "correcao_sugerida": issues["suggested_fix"],
            "geometria_wkt": issues["geometry_wkt"],
        }
    )


def _summarize(issues: pd.DataFrame) -> pd.DataFrame:
    if issues.empty:
        return pd.DataFrame(columns=["domain", "theme", "regra_id", "severity", "total_erros"])
    return (
        issues.groupby(["domain", "theme", "regra_id", "severity"], dropna=False)
        .size()
        .reset_index(name="total_erros")
        .sort_values(["severity", "theme", "regra_id"])
    )


def _parse_wkt(value):
    if wkt is None or pd.isna(value) or not str(value).strip():
        return None
    try:
        return wkt.loads(str(value))
    except Exception:
        return None


def _write_error_gpkg(issues: pd.DataFrame, path: Path) -> None:
    if issues.empty or gpd is None:
        return
    geoms = issues["geometry_wkt"].apply(_parse_wkt)
    if geoms.isna().all():
        return
    gdf = gpd.GeoDataFrame(issues.copy(), geometry=geoms, crs="EPSG:3763")
    gdf = gdf[gdf.geometry.notna()].copy()
    if not gdf.empty:
        path.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(path, layer="validacao_erros", driver="GPKG")


def validate_run(
    run_dir: str | Path,
    *,
    domain: str,
    run_id: str,
    tolerances_path: str | Path | None = None,
    stages: set[str] | None = None,
) -> pd.DataFrame:
    """Run validations over normalized exports and write final error outputs."""

    stages = stages or {"geometry", "attributes", "topology", "metadata"}
    run_dir = Path(run_dir)
    errors_dir = run_dir / "erros"
    reports_dir = run_dir / "relatorios"
    errors_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = load_normalized_with_geometry(run_dir)
    prefix = _domain_prefix(domain)
    tolerances = _read_tolerances(tolerances_path)

    frames: list[pd.DataFrame] = []
    if "geometry" in stages:
        frames.append(
            validate_geometry(
                df,
                zero_length_threshold_m=float(tolerances.get("zero_length_threshold_m", 0.05) or 0.05),
                domain=domain,
                code_prefix=prefix,
                run_id=run_id,
            )
        )

    if "attributes" in stages:
        for group in ["LINK", "NODE", "RAMAL", "ZONE"]:
            subset = _filter_by_group(df, group)
            if not subset.empty:
                frames.append(validate_required_attributes(subset, group, domain=domain, code_prefix=prefix, run_id=run_id))

    if "metadata" in stages:
        frames.append(validate_location_metadata(df, domain=domain, code_prefix=prefix, run_id=run_id))

    if "topology" in stages:
        links = _filter_by_group(df, "LINK")
        nodes = _filter_by_group(df, "NODE")
        frames.append(
            validate_nodes_links(
                links,
                nodes,
                tolerances,
                code_prefix=prefix,
                link_term=_link_term(domain),
                domain=domain,
                run_id=run_id,
            )
        )

    issues = _combine_frames(frames, domain=domain, run_id=run_id)
    readable = _make_readable(issues)
    summary = _summarize(issues)
    sample = readable.head(50).copy()

    write_csv(issues, errors_dir / "validacao_erros.csv")
    write_excel(issues, errors_dir / "validacao_erros.xlsx")
    write_csv(readable, errors_dir / "validacao_erros_legivel.csv")
    write_excel(readable, errors_dir / "validacao_erros_legivel.xlsx")
    write_csv(summary, reports_dir / "resumo_erros_por_regra.csv")
    write_excel(summary, reports_dir / "resumo_erros_por_regra.xlsx")
    write_csv(sample, reports_dir / "amostra_casos_reais.csv")
    write_excel(sample, reports_dir / "amostra_casos_reais.xlsx")
    _write_error_gpkg(issues, errors_dir / "validacao_erros.gpkg")

    return issues
