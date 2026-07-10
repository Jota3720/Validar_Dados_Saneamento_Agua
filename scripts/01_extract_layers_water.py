from __future__ import annotations

import argparse
import io
import os
import subprocess
from pathlib import Path

import _bootstrap  # noqa: F401
import geopandas as gpd
import pandas as pd
from shapely import wkt

from src.config_loader import ensure_output_dirs, load_yaml
from src.io import setup_logging
from src.normalization import normalize_links, normalize_nodes
from src.oracle_extract import diagnose_wkt_text


class SqlPlusClient:
    def __init__(self, config_path: str):
        cfg = load_yaml(config_path)["oracle"]
        self.user = cfg["user"]
        self.password = cfg["password"]
        self.dsn = cfg["dsn"]
        self.sqlplus_path = cfg.get("sqlplus_path", r"C:\\Oracle\\product\\19.0.0\\client_1\\bin\\sqlplus.exe")
        self.tns_admin = cfg.get("config_dir")

    def query(self, sql: str) -> pd.DataFrame:
        sql_text = sql.strip()
        if not sql_text.endswith(";"):
            sql_text += ";"
        script = "\n".join(
            [
                "set pagesize 0",
                "set feedback off",
                "set verify off",
                "set trimspool on",
                "set linesize 32767",
                "set long 10000000",
                "set longchunksize 10000000",
                "set tab off",
                "set markup csv on delimiter , quote on",
                sql_text,
                "exit",
            ]
        )
        env = os.environ.copy()
        if self.tns_admin:
            env["TNS_ADMIN"] = self.tns_admin
        proc = subprocess.run(
            [self.sqlplus_path, "-s", f"{self.user}/{self.password}@{self.dsn}"],
            input=script,
            text=True,
            capture_output=True,
            env=env,
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(message or f"sqlplus falhou com codigo {proc.returncode}")
        text = (proc.stdout or "").strip()
        if not text:
            return pd.DataFrame()
        return pd.read_csv(io.StringIO(text))


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrai layers de agua em modo read-only via SQL*Plus.")
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
        client = SqlPlusClient(args.database_config)
        link_layers = _extract_group(client, mapping.get("links", {}))
        node_layers = _extract_group(client, mapping.get("nodes", {}))
        zone_layers = _extract_group(client, mapping.get("zones", {}))
    except Exception as exc:
        print(f"Falha na extracao Oracle read-only: {exc}")
        return 2

    if link_layers:
        links = normalize_links(link_layers, mapping["links"])
        _write_outputs(links, output_dir / f"{args.output_prefix}_links")
    if node_layers:
        nodes = normalize_nodes(node_layers, mapping["nodes"])
        _write_outputs(nodes, output_dir / f"{args.output_prefix}_nodes")
    for name, gdf in zone_layers.items():
        _write_outputs(_combine_zones({name: gdf}, mapping.get("zones", {})), output_dir / f"{args.output_prefix}_zones")

    print("Extracao/normalizacao de agua concluida.")
    return 0


def _extract_group(client: SqlPlusClient, group_cfg: dict) -> dict[str, gpd.GeoDataFrame]:
    layers = {}
    for layer_name, cfg in group_cfg.items():
        if not cfg.get("include", False):
            continue
        source = cfg["source"]
        owner, table = source.split(".", 1)
        geom_col = cfg["geometry_column"]
        available_df = client.query(
            f"""
            SELECT column_name
            FROM all_tab_columns
            WHERE owner = '{owner.upper()}'
              AND table_name = '{table.upper()}'
            ORDER BY column_id
            """
        )
        available_cols = {str(v).upper() for v in available_df.get("COLUMN_NAME", [])}
        if "IPID" not in available_cols:
            available_cols.add("IPID")
        select_fields = [field for field in _build_select_fields(cfg, geom_col) if field.upper() in available_cols]
        if "IPID" not in {f.upper() for f in select_fields}:
            select_fields.insert(0, "IPID")
        select_sql = ", ".join(f't."{field}" AS "{field}"' for field in select_fields)
        sql = f'SELECT {select_sql}, SDO_UTIL.TO_WKTGEOMETRY(t."{geom_col}") AS WKT_GEOM FROM "{owner}"."{table}" t'
        df = client.query(sql)
        if "WKT_GEOM" not in df.columns:
            raise RuntimeError(f"Extracao sem coluna WKT para {source}")
        audits = pd.DataFrame([diagnose_wkt_text(value) for value in df["WKT_GEOM"].tolist()])
        audits = audits.drop(columns=["geometry"], errors="ignore")
        geometry = df["WKT_GEOM"].apply(_safe_wkt)
        df = pd.concat([df, audits], axis=1)
        drop_cols = ["WKT_GEOM", geom_col]
        geom_like = [
            col
            for col in df.columns
            if str(col).upper().startswith(f"{geom_col.upper()}(") or str(col).upper().startswith("SDO_GEOMETRY(")
        ]
        drop_cols.extend(geom_like)
        gdf = gpd.GeoDataFrame(df.drop(columns=drop_cols, errors="ignore"), geometry=geometry)
        if cfg.get("crs_epsg"):
            gdf = gdf.set_crs(epsg=int(cfg["crs_epsg"]), allow_override=True)
        layers[layer_name] = gdf
    return layers


def _build_select_fields(cfg: dict, geom_col: str) -> list[str]:
    fields = [
        cfg.get("id_field"),
        cfg.get("entity_code_field"),
        cfg.get("parent_entity_code_field"),
        "ARRUAMENTO",
        "COD_ARRUAMENTO",
        "CODIGO_ARRUAMENTO_SAP",
        "FREGUESIA",
        "FREGUESIA_CAOP_2012",
        "FREGUESIA_CAOP_2017",
        "NUMERO_DE_POLICIA",
        "NUMERO_POLICIA",
        "NPOLICIA",
        "NP",
        cfg.get("status_field"),
        cfg.get("system_type_field"),
        cfg.get("system_field"),
        cfg.get("subsystem_field"),
        cfg.get("zmc_field"),
        cfg.get("diameter_field"),
        cfg.get("material_field"),
        cfg.get("length_field"),
        cfg.get("pressure_field"),
        cfg.get("pressure_nominal_field"),
        cfg.get("slope_field"),
        cfg.get("regime_field"),
        cfg.get("burial_depth_field"),
        cfg.get("cover_level_field"),
        cfg.get("invert_level_field"),
        cfg.get("ground_level_field"),
        cfg.get("node_type_field"),
        cfg.get("name_field"),
    ]
    ordered = []
    seen = set()
    for field in fields:
        if not field:
            continue
        field = str(field).strip()
        if not field or field == geom_col or field in seen:
            continue
        seen.add(field)
        ordered.append(field)
    return ordered


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
    table.to_csv(base_path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    table.to_excel(base_path.with_suffix(".xlsx"), index=False)
    try:
        gdf.to_file(base_path.with_suffix(".gpkg"), layer=base_path.stem, driver="GPKG")
    except Exception:
        pass


def _gdf_to_table(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    out = gdf.copy()
    if "geometry" in out.columns:
        out["geometry_wkt"] = out["geometry"].apply(lambda geom: geom.wkt if geom is not None else "")
        out = out.drop(columns=["geometry"])
    return pd.DataFrame(out)


def _safe_wkt(value):
    if pd.isna(value) or value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return wkt.loads(text)
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
