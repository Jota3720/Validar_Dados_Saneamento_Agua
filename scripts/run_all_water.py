from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import CRS
from shapely import wkt

from _bootstrap import ROOT
from src.attribute_rules import validate_required_attributes
from src.config_loader import load_yaml
from src.geometry_rules import validate_geometry
from src.io import write_csv, write_excel
from src.issue_schema import empty_issues
from src.metadata_rules import validate_location_metadata
from src.reporting import errors_to_gdf, generate_report, write_error_outputs, write_extraction_integrity_report
from src.rule_catalog import catalog_for_domain
from src.run_context import create_run_context
from src.topology_rules import validate_nodes_links


def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else Path(ROOT, p)


def run_pipeline(config_path: str | Path = "config/project_water.yaml", *, skip_extract: bool = False) -> Path:
    config_path = _resolve_path(config_path)
    cfg = load_yaml(config_path)
    domain = cfg.get("domain", "AGUA")
    outputs_root = _resolve_path(cfg.get("outputs_root", "outputs"))
    ctx = create_run_context(outputs_root, domain)
    database_config = _resolve_path(cfg.get("database_config", "config/database.yaml"))
    skip_extract = skip_extract or bool(cfg.get("skip_extract", False))

    if not skip_extract:
        _run_extraction(
            script_name="01_extract_layers_water.py",
            config_path=_resolve_path(cfg.get("layers_mapping", "config/layers_mapping_water.yaml")),
            database_config=database_config,
        )

    rules_path = _resolve_path(cfg.get("rules_catalog", "config/rules_catalog.yaml"))
    rules = catalog_for_domain(rules_path, domain)
    write_csv(rules, ctx.reports_dir / "catalogo_regras.csv")
    write_excel(rules, ctx.reports_dir / "catalogo_regras.xlsx")
    write_csv(rules, Path(ROOT) / "outputs" / "relatorios" / "catalogo_regras.csv")
    write_excel(rules, Path(ROOT) / "outputs" / "relatorios" / "catalogo_regras.xlsx")

    links = _read_csv_gdf(Path(ROOT) / "outputs" / "exports" / "wat_links.csv")
    nodes = _read_csv_gdf(Path(ROOT) / "outputs" / "exports" / "wat_nodes.csv")
    write_extraction_integrity_report({"links": links, "nodes": nodes}, ctx.root, report_stem="diagnostico_integridade_extracao")

    tolerances = load_yaml(cfg.get("tolerances", "config/tolerancias.yaml"))
    errors: list[pd.DataFrame] = []
    errors.append(
        validate_geometry(
            links,
            zero_length_threshold_m=float(tolerances.get("zero_length_threshold_m", 0.05) or 0.05),
            domain=domain,
            code_prefix="WAT",
            run_id=ctx.run_id,
        )
    )
    errors.append(
        validate_geometry(
            nodes,
            zero_length_threshold_m=float(tolerances.get("zero_length_threshold_m", 0.05) or 0.05),
            domain=domain,
            code_prefix="WAT",
            run_id=ctx.run_id,
        )
    )

    if _is_metric_crs(links.crs or nodes.crs):
        errors.append(
            validate_nodes_links(
                links,
                nodes,
                tolerances,
                code_prefix="WAT",
                link_term="tubagem",
                source_layer_alias="GIA.A",
                allow_link_link_endpoint_connections=True,
                domain=domain,
                run_id=ctx.run_id,
            )
        )
    elif cfg.get("validation", {}).get("stop_on_crs_error", True):
        print(f"Topologia bloqueada por CRS nao metrico ou em falta: {links.crs or nodes.crs}")

    errors.append(validate_required_attributes(links, "LINK", domain=domain, code_prefix="WAT", run_id=ctx.run_id))
    errors.append(validate_required_attributes(nodes, "NODE", domain=domain, code_prefix="WAT", run_id=ctx.run_id))
    errors.append(validate_location_metadata(links, domain=domain, code_prefix="WAT", run_id=ctx.run_id))
    errors.append(validate_location_metadata(nodes, domain=domain, code_prefix="WAT", run_id=ctx.run_id))

    issues = errors_to_gdf(pd.concat(errors, ignore_index=True) if errors else empty_issues(), crs=links.crs or nodes.crs)
    output_stem = f"ERROS_MODELO_AGUA_{ctx.run_id}"
    report_stem = f"relatorio_validacao_agua_{ctx.run_id}"
    write_error_outputs(issues, ctx.root, output_stem=output_stem)
    meta = {
        "data_source": "outputs/exports/wat_links.csv / wat_nodes.csv",
        "crs": str(links.crs or nodes.crs or ""),
        "links_count": len(links),
        "nodes_count": len(nodes),
        "ramais_count": 0,
    }
    generate_report(
        issues,
        meta,
        ctx.root,
        report_stem=report_stem,
        title="Agua",
        rule_summary_name=f"resumo_erros_por_regra_agua_{ctx.run_id}.csv",
    )

    print(f"Pipeline concluido: {len(issues)} erros/anomalias.")
    print(f"Output principal: {ctx.root / 'erros' / f'{output_stem}.shp'}")
    return ctx.root


def _run_extraction(*, script_name: str, config_path: Path, database_config: Path) -> None:
    script = Path(ROOT) / "scripts" / script_name
    if not script.exists():
        raise FileNotFoundError(f"Script de extracao nao encontrado: {script}")
    cmd = [
        sys.executable,
        str(script),
        "--config",
        str(config_path),
        "--database-config",
        str(database_config),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(message or f"Extracao falhou com codigo {proc.returncode}")


def _read_csv_gdf(path: Path) -> gpd.GeoDataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    wkt_column = None
    for candidate in ("WKT", "geometry_wkt", "GEOMETRY_WKT"):
        if candidate in df.columns:
            wkt_column = candidate
            break
    if wkt_column is None:
        raise RuntimeError(f"CSV sem coluna WKT/geometry_wkt: {path}")
    geometry = gpd.GeoSeries([_safe_wkt(value) for value in df[wkt_column]], crs=3763)
    return gpd.GeoDataFrame(df, geometry=geometry, crs=3763)


def _safe_wkt(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return wkt.loads(text)
    except Exception:
        return None


def _is_metric_crs(crs_value) -> bool:
    if crs_value is None:
        return False
    try:
        crs = CRS.from_user_input(crs_value)
    except Exception:
        return False
    return bool(crs.is_projected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa o pipeline de validacao de agua.")
    parser.add_argument("--config", default="config/project_water.yaml")
    parser.add_argument("--skip-extract", action="store_true", help="Nao executa a extracao Oracle.")
    args = parser.parse_args(argv)
    run_dir = run_pipeline(args.config, skip_extract=args.skip_extract)
    print(f"Run criada em: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
