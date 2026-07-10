from __future__ import annotations

from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt

from .config_loader import ensure_output_dirs
from .io import write_csv, write_excel


ERROR_COLUMNS = [
    "error_id",
    "regra_id",
    "categoria",
    "tipo_erro",
    "gravidade",
    "source_layer",
    "source_layer_detail",
    "source_id",
    "related_layer",
    "related_id",
    "tolerancia_m",
    "descricao",
    "acao_sugerida",
    "data_execucao",
    "confidence",
    "falso_positivo_possivel",
    "geometry",
]


def errors_to_gdf(errors, crs=None) -> gpd.GeoDataFrame:
    if isinstance(errors, pd.DataFrame):
        df = errors.copy()
    else:
        df = pd.DataFrame(errors)
    if df.empty:
        return gpd.GeoDataFrame(columns=ERROR_COLUMNS, geometry=[], crs=crs)
    if "geometry" not in df.columns and "geometry_wkt" in df.columns:
        df["geometry"] = df["geometry_wkt"].apply(_safe_wkt)
    elif "geometry" not in df.columns:
        df["geometry"] = None
    df = df.copy()
    if "error_id" not in df.columns:
        df["error_id"] = [f"ERR_{i:07d}" for i in range(1, len(df) + 1)]
    for col in ERROR_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return gpd.GeoDataFrame(df[ERROR_COLUMNS], geometry="geometry", crs=crs)


def write_error_outputs(
    errors_gdf: gpd.GeoDataFrame,
    outputs_root: str | Path = "outputs",
    output_stem: str = "ERROS_MODELO_SANEAMENTO",
) -> None:
    paths = ensure_output_dirs(outputs_root)
    _remove_existing_vector_outputs(paths["errors"] / output_stem)
    if errors_gdf.empty:
        pd.DataFrame(columns=ERROR_COLUMNS[:-1]).to_csv(paths["errors"] / f"{output_stem}.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(columns=ERROR_COLUMNS[:-1]).to_excel(paths["errors"] / f"{output_stem}.xlsx", index=False)
        return
    shape_gdf = _errors_as_point_gdf(errors_gdf)
    shp_path = paths["errors"] / f"{output_stem}.shp"
    shape_gdf.to_file(shp_path, driver="ESRI Shapefile")
    gpkg_path = paths["errors"] / f"{output_stem}.gpkg"
    try:
        shape_gdf.to_file(gpkg_path, layer="erros", driver="GPKG")
    except Exception:
        if gpkg_path.exists():
            try:
                gpkg_path.unlink()
            except Exception:
                pass
    errors_gdf.drop(columns="geometry").to_csv(paths["errors"] / f"{output_stem}.csv", index=False, encoding="utf-8-sig")
    errors_gdf.drop(columns="geometry").to_excel(paths["errors"] / f"{output_stem}.xlsx", index=False)
    for regra_id, subset in errors_gdf.groupby("regra_id"):
        name = f"{regra_id}_{_slug(subset['tipo_erro'].iloc[0])}.shp"
        try:
            _errors_as_point_gdf(subset).to_file(paths["errors"] / name, driver="ESRI Shapefile")
        except Exception:
            continue


def generate_report(
    errors_gdf: gpd.GeoDataFrame,
    meta: dict,
    outputs_root: str | Path = "outputs",
    report_stem: str = "relatorio_validacao_saneamento",
    title: str = "Saneamento",
    rule_summary_name: str = "resumo_erros_por_regra.csv",
) -> None:
    paths = ensure_output_dirs(outputs_root)
    df = pd.DataFrame(errors_gdf.drop(columns="geometry", errors="ignore"))
    total = len(df)
    by_rule = df.groupby(["regra_id", "categoria", "tipo_erro", "gravidade"]).size().reset_index(name="ocorrencias") if total else pd.DataFrame()
    by_gravity = df.groupby("gravidade").size().reset_index(name="ocorrencias") if total else pd.DataFrame()
    by_category = df.groupby("categoria").size().reset_index(name="ocorrencias") if total else pd.DataFrame()
    by_rule.to_csv(paths["reports"] / rule_summary_name, index=False, encoding="utf-8-sig")

    ready_score = _readiness_score(df, meta)
    md = [
        f"# Relatorio de Validacao de Cadastro de {title}",
        "",
        f"Data de execucao: {datetime.now().isoformat(timespec='seconds')}",
        f"Fonte dos dados: {meta.get('data_source', 'ficheiros locais / configuracao')}",
        f"CRS/SRID: {meta.get('crs', 'nao indicado')}",
        "",
        "## Layers analisadas",
        "",
        f"- Links: {meta.get('links_count', 0)}",
        f"- Nodes/CVs: {meta.get('nodes_count', 0)}",
        f"- Ramais: {meta.get('ramais_count', 0)}",
        "",
        "## Resumo",
        "",
        f"- Total de erros/anomalias: {total}",
        f"- Percentagem estimada da rede pronta para modelacao: {ready_score:.1f}%",
        "",
        "## Erros por categoria",
        "",
        _table_block(by_category) if not by_category.empty else "Sem ocorrencias.",
        "",
        "## Erros por gravidade",
        "",
        _table_block(by_gravity) if not by_gravity.empty else "Sem ocorrencias.",
        "",
        "## Top 10 regras",
        "",
        _table_block(by_rule.sort_values("ocorrencias", ascending=False).head(10)) if not by_rule.empty else "Sem ocorrencias.",
        "",
        "## Recomendacoes por prioridade",
        "",
        "1. Corrigir primeiro erros CRITICA ligados a endpoints sem nos, geometrias invalidas e IDs duplicados.",
        "2. Rever erros ALTA de snapping, diametros em falta e nos isolados.",
        "3. Validar anomalias MEDIA/AVISO que podem ser falsos positivos operacionais.",
    ]
    md_path = paths["reports"] / f"{report_stem}.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    html = "<html><meta charset='utf-8'><body>" + "\n".join(_markdown_to_simple_html(line) for line in md) + "</body></html>"
    (paths["reports"] / f"{report_stem}.html").write_text(html, encoding="utf-8")


def write_report_tables(df: pd.DataFrame, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(df, out / "resumo_erros_por_regra.csv")
    write_excel(df, out / "resumo_erros_por_regra.xlsx")


def write_extraction_integrity_report(
    frames: dict[str, gpd.GeoDataFrame],
    outputs_root: str | Path = "outputs",
    report_stem: str = "diagnostico_integridade_extracao",
) -> None:
    paths = ensure_output_dirs(outputs_root)
    summary_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []

    for dataset_name, gdf in frames.items():
        df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore")).copy()
        if df.empty:
            summary_rows.append(
                {
                    "dataset": dataset_name,
                    "layer": dataset_name,
                    "rows": 0,
                    "with_wkt": 0,
                    "parse_ok": 0,
                    "parse_failed": 0,
                    "null_geometry": 0,
                    "invalid_geometry": 0,
                    "unsupported_geometry": 0,
                    "truncated_wkt": 0,
                }
            )
            continue

        layer_values = df["source_layer"] if "source_layer" in df.columns else pd.Series([dataset_name] * len(df), index=df.index)
        if "diagnostic_reason" not in df.columns:
            df["diagnostic_reason"] = "OK"
        if "geometry_parse_ok" not in df.columns:
            df["geometry_parse_ok"] = True
        if "geometry_is_valid" not in df.columns:
            df["geometry_is_valid"] = True

        grouped = df.groupby(layer_values, dropna=False)
        for layer_name, subset in grouped:
            reason = subset["diagnostic_reason"].fillna("OK").astype(str)
            length_series = pd.to_numeric(
                subset["extracted_wkt_length"], errors="coerce"
            ) if "extracted_wkt_length" in subset.columns else pd.Series([0] * len(subset), index=subset.index)
            summary_rows.append(
                {
                    "dataset": dataset_name,
                    "layer": layer_name,
                    "rows": int(len(subset)),
                    "with_wkt": int((length_series.fillna(0) > 0).sum()) if len(subset) else 0,
                    "parse_ok": int((subset["geometry_parse_ok"] == True).sum()),  # noqa: E712
                    "parse_failed": int(reason.isin(["WKT_PARSE_FAILED", "WKT_TRUNCATED"]).sum()),
                    "null_geometry": int(reason.eq("NULL_GEOMETRY").sum()),
                    "invalid_geometry": int(reason.eq("INVALID_GEOMETRY").sum()),
                    "unsupported_geometry": int(reason.eq("UNSUPPORTED_GEOMETRY").sum()),
                    "truncated_wkt": int(reason.eq("WKT_TRUNCATED").sum()),
                }
            )

            failed = subset.loc[reason.ne("OK")].copy()
            if not failed.empty:
                for _, row in failed.iterrows():
                    detail_rows.append(
                        {
                            "dataset": dataset_name,
                            "layer": layer_name,
                            "source_id": row.get("source_id"),
                            "source_wkt_length": row.get("source_wkt_length"),
                            "extracted_wkt_length": row.get("extracted_wkt_length"),
                            "geometry_parse_ok": row.get("geometry_parse_ok"),
                            "geometry_type": row.get("geometry_type"),
                            "geometry_is_valid": row.get("geometry_is_valid"),
                            "diagnostic_reason": row.get("diagnostic_reason"),
                            "parse_error": row.get("parse_error"),
                            "wkt_original": row.get("wkt_original"),
                        }
                    )

    summary = pd.DataFrame(summary_rows)
    details = pd.DataFrame(detail_rows)
    write_csv(summary, paths["reports"] / f"{report_stem}.csv")
    with pd.ExcelWriter(paths["reports"] / f"{report_stem}.xlsx", engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Resumo", index=False)
        details.to_excel(writer, sheet_name="Falhas", index=False)


def _safe_wkt(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return wkt.loads(text)
    except Exception:
        return None


def _errors_as_point_gdf(errors_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = errors_gdf.copy()
    gdf["geometry"] = gdf["geometry"].apply(_as_point_geometry)
    return gpd.GeoDataFrame(gdf, geometry="geometry", crs=errors_gdf.crs)


def _as_point_geometry(geom):
    if geom is None or getattr(geom, "is_empty", False):
        return None
    geom_type = getattr(geom, "geom_type", "")
    if geom_type == "Point":
        return geom
    try:
        return geom.representative_point()
    except Exception:
        try:
            return geom.centroid
        except Exception:
            return None


def _remove_existing_vector_outputs(base: Path) -> None:
    for suffix in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix", ".fix", ".gpkg"]:
        target = base.with_suffix(suffix)
        if target.exists():
            try:
                target.unlink()
            except Exception:
                pass


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_")[:80]


def _readiness_score(df: pd.DataFrame, meta: dict) -> float:
    total_features = max(int(meta.get("links_count", 0)) + int(meta.get("nodes_count", 0)), 1)
    critical = int((df.get("gravidade") == "CRITICA").sum()) if not df.empty else 0
    high = int((df.get("gravidade") == "ALTA").sum()) if not df.empty else 0
    penalty = (critical * 4 + high * 2) / total_features
    return max(0.0, min(100.0, 100.0 - penalty * 10.0))


def _markdown_to_simple_html(line: str) -> str:
    if line.startswith("# "):
        return f"<h1>{line[2:]}</h1>"
    if line.startswith("## "):
        return f"<h2>{line[3:]}</h2>"
    if line.startswith("- "):
        return f"<li>{line[2:]}</li>"
    if line.strip() == "":
        return "<br/>"
    return f"<p>{line}</p>"


def _table_block(df: pd.DataFrame) -> str:
    if df.empty:
        return "Sem ocorrencias."
    return "\n".join(["```text", df.to_string(index=False), "```"])
