from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
import geopandas as gpd
import pandas as pd

from src.config_loader import ensure_output_dirs, load_yaml
from src.db import oracle_connection
from src.io import setup_logging, write_csv, write_excel, write_gdf
from src.normalization import normalize_links, normalize_nodes
from src.oracle_extract import extract_group


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrai layers de agua em modo read-only via Oracle.")
    parser.add_argument("--config", default="config/layers_mapping_water.yaml")
    parser.add_argument("--database-config", default="config/database.yaml")
    parser.add_argument("--output-prefix", default="wat")
    parser.add_argument("--output-dir", default="outputs/exports")
    args = parser.parse_args()

    paths = ensure_output_dirs("outputs")
    setup_logging(paths["logs"] / "01_extract_layers_water.log")
    mapping = load_yaml(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with oracle_connection(args.database_config) as conn:
            link_layers = extract_group(conn, mapping.get("links", {}))
            node_layers = extract_group(conn, mapping.get("nodes", {}))
            zone_layers = extract_group(conn, mapping.get("zones", {}))
    except Exception as exc:
        print(f"Falha na extracao Oracle read-only: {exc}")
        return 2

    if link_layers:
        links = normalize_links(link_layers, mapping["links"])
        _write_outputs(links, output_dir / f"{args.output_prefix}_links")
    if node_layers:
        nodes = normalize_nodes(node_layers, mapping["nodes"])
        _write_outputs(nodes, output_dir / f"{args.output_prefix}_nodes")
    if zone_layers:
        zones = _combine_zones(zone_layers, mapping.get("zones", {}))
        _write_outputs(zones, output_dir / f"{args.output_prefix}_zones")

    print("Extracao/normalizacao de agua concluida.")
    return 0


def _combine_zones(zone_layers: dict[str, gpd.GeoDataFrame], mapping: dict) -> gpd.GeoDataFrame:
    frames: list[gpd.GeoDataFrame] = []
    for layer_name, gdf in zone_layers.items():
        cfg = mapping.get(layer_name, {})
        out = gdf.copy()
        out["source_layer"] = layer_name
        out["source_id"] = _field(gdf, cfg.get("id_field"))
        out["entity_type"] = cfg.get("entity_type", layer_name)
        out["model_group"] = "ZONE"
        out["include_in_model"] = bool(cfg.get("include_in_model", True))
        frames.append(out)
    if not frames:
        return gpd.GeoDataFrame(geometry=[])
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=frames[0].crs)


def _field(gdf: gpd.GeoDataFrame, field: str | None) -> pd.Series:
    if field and field in gdf.columns:
        return gdf[field]
    return pd.Series([None] * len(gdf), index=gdf.index)


def _write_outputs(gdf: gpd.GeoDataFrame, base_path: Path) -> None:
    table = _gdf_to_table(gdf)
    write_csv(table, base_path.with_suffix(".csv"))
    write_excel(table, base_path.with_suffix(".xlsx"))
    write_gdf(gdf, base_path.with_suffix(".gpkg"))


def _gdf_to_table(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    out = gdf.copy()
    if "geometry" in out.columns:
        out["geometry_wkt"] = out["geometry"].apply(lambda geom: geom.wkt if geom is not None else "")
        out = out.drop(columns=["geometry"])
    return pd.DataFrame(out)


if __name__ == "__main__":
    raise SystemExit(main())
