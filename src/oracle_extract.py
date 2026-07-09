from __future__ import annotations

from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt

from .db import list_columns, read_sql


COMMON_FIELD_CANDIDATES = [
    "IPID",
    "ID",
    "OBJECTID",
    "FID",
    "CODIGO_DA_ENTIDADE",
    "CODIGO_DA_ENTIDADE_PAI",
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
    "ESTADO",
    "STATUS",
    "TIPO_REDE",
    "SISTEMA",
    "SUBSISTEMA",
    "BACIA",
    "ZMC",
    "DIAMETRO",
    "DIAMETRO_NOMINAL",
    "DIAMETRO_NOMINAL_MM",
    "MATERIAL",
    "COMPRIMENTO",
    "COMPRIMENTO_M",
    "PENDENTE",
    "DECLIVE",
    "REGIME_ESCOAMENTO",
    "COTA_DA_TAMPA_M",
    "COTA_DE_SOLEIRA_M",
    "COTA_DO_TERRENO_M",
    "COTA_MONTANTE",
    "COTA_JUSANTE",
    "TIPO_HIDRANTE",
    "TIPO_NO_ALTERACAO",
    "TIPO_DE_VALVULA",
    "TIPO_DE_SECCAO",
    "TIPO_DE_JUNTA",
    "TIPO_DE_ASSENTAMENTO",
    "TIPO_RECOBRIMENTO",
    "FABRICANTE",
    "PRESSAO_NOMINAL_BAR",
    "PRESSAO_DE_SERVICO_BAR",
    "NAME",
    "NOME",
]


def extract_layer_gdf(conn, owner: str, table_name: str, geom_col: str, cfg: dict[str, Any]) -> gpd.GeoDataFrame:
    owner = owner.upper().strip()
    table_name = table_name.upper().strip()
    geom_col = geom_col.strip()
    available = _available_columns(conn, owner, table_name)
    if geom_col.upper() not in available:
        raise RuntimeError(f"Coluna de geometria '{geom_col}' nao encontrada em {owner}.{table_name}")

    select_fields = _build_select_fields(cfg, available, geom_col)
    if cfg.get("id_field") and cfg["id_field"].upper() not in {f.upper() for f in select_fields}:
        if cfg["id_field"].upper() in available:
            select_fields.insert(0, cfg["id_field"])
    if "IPID" in available and "IPID" not in {f.upper() for f in select_fields}:
        select_fields.insert(0, "IPID")

    select_sql = ", ".join(f't."{field}" AS "{field}"' for field in select_fields)
    sql = f'SELECT {select_sql}, SDO_UTIL.TO_WKTGEOMETRY(t."{geom_col}") AS WKT_GEOM FROM "{owner}"."{table_name}" t'
    df = read_sql(conn, sql)
    if "WKT_GEOM" not in df.columns:
        raise RuntimeError(f"Extracao sem coluna WKT para {owner}.{table_name}")

    geometry = df["WKT_GEOM"].apply(_safe_wkt)
    drop_cols = {"WKT_GEOM", geom_col}
    for col in list(df.columns):
        if str(col).upper().startswith("SDO_GEOMETRY("):
            drop_cols.add(col)
        if str(col).upper().startswith(f"{geom_col.upper()}("):
            drop_cols.add(col)

    gdf = gpd.GeoDataFrame(df.drop(columns=list(drop_cols), errors="ignore"), geometry=geometry)
    if cfg.get("crs_epsg"):
        gdf = gdf.set_crs(epsg=int(cfg["crs_epsg"]), allow_override=True)
    return gdf


def extract_group(conn, group_cfg: dict[str, Any]) -> dict[str, gpd.GeoDataFrame]:
    layers: dict[str, gpd.GeoDataFrame] = {}
    for layer_name, cfg in (group_cfg or {}).items():
        if not cfg.get("include", False):
            continue
        source = cfg.get("source")
        geom_col = cfg.get("geometry_column", "GEOMETRY")
        if not source or "." not in source:
            raise ValueError(f"Layer '{layer_name}' sem source valida (esperado OWNER.TABELA).")
        owner, table_name = source.split(".", 1)
        layers[layer_name] = extract_layer_gdf(conn, owner, table_name, geom_col, cfg)
    return layers


def _available_columns(conn, owner: str, table_name: str) -> set[str]:
    cols = list_columns(conn, owner, table_name)
    if cols.empty:
        return set()
    return {str(name).upper() for name in cols["COLUMN_NAME"].tolist()}


def _build_select_fields(cfg: dict[str, Any], available: set[str], geom_col: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    explicit = cfg.get("select_fields") or cfg.get("fields") or []
    if isinstance(explicit, str):
        explicit = [part.strip() for part in explicit.split(";") if part.strip()]

    fields: list[str | None] = [
        cfg.get("id_field"),
        cfg.get("entity_code_field"),
        cfg.get("parent_entity_code_field"),
        *explicit,
        *COMMON_FIELD_CANDIDATES,
        cfg.get("status_field"),
        cfg.get("system_type_field"),
        cfg.get("system_field"),
        cfg.get("subsystem_field"),
        cfg.get("basin_field"),
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
        cfg.get("upstream_node_field"),
        cfg.get("downstream_node_field"),
    ]

    for field in fields:
        if not field:
            continue
        field = str(field).strip()
        upper = field.upper()
        if not field or upper == geom_col.upper() or upper in seen:
            continue
        if upper in available:
            seen.add(upper)
            ordered.append(field)
    return ordered


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
