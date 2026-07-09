from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd


FIELD_HINTS = {
    "possible_id_fields": ["IPID", "ID", "OBJECTID", "FID", "COD", "CODIGO", "NUMERO", "REF"],
    "possible_status_fields": ["ESTADO", "STATUS", "SITUACAO", "ATIVO", "ACTIVO"],
    "possible_diameter_fields": ["DIAM", "DIAMETRO", "DN", "CALIBRE"],
    "possible_material_fields": ["MATERIAL", "MAT", "TIPO_MATERIAL"],
    "possible_elevation_fields": ["COTA", "SOLEIRA", "TAMPA", "INVERT", "Z", "ALTIM"],
    "possible_network_type_fields": ["TIPO_REDE", "REDE", "SISTEMA", "TIPO_SANEAMENTO"],
    "possible_zone_fields": ["BACIA", "SUBSISTEMA", "ZONA", "DRENAGEM"],
    "possible_date_fields": ["DATA", "DT_", "DATE", "EDICAO", "CRIACAO", "ALTERACAO"],
}

LINK_WORDS = ["COLET", "COLECT", "TROCO", "TROÇO", "EMISS", "CONDUTA", "RAMAL", "TUB", "INTERC"]
NODE_WORDS = ["CV", "CAIX", "CAMARA", "CAMÂRA", "ESTACAO", "ESTAÇÃO", "DESCARGA", "OUTFALL", "NO_", "NÓ"]
ZONE_WORDS = ["BACIA", "SUBSISTEMA", "ZONA", "DRENAGEM"]
SUPPORT_WORDS = ["RUA", "ARRU", "LIMITE", "FREG", "CONCELHO", "ORTO", "REFER"]


def summarize_columns(columns_df: pd.DataFrame) -> dict:
    names = [str(c).upper() for c in columns_df["COLUMN_NAME"].tolist()]
    result = {"fields": ";".join(names)}
    for key, hints in FIELD_HINTS.items():
        result[key] = ";".join([name for name in names if any(h in name for h in hints)])
    return result


def classify_layer(table_name: str, geometry_type: str | None) -> str:
    name = table_name.upper()
    gtype = (geometry_type or "").upper()
    if any(w in name for w in ZONE_WORDS) or "POLYGON" in gtype:
        return "ZONE"
    if any(w in name for w in NODE_WORDS) or "POINT" in gtype:
        return "NODE"
    if any(w in name for w in LINK_WORDS) or "LINE" in gtype:
        return "LINK"
    if any(w in name for w in SUPPORT_WORDS):
        return "SUPPORT"
    return "UNKNOWN"


def build_layers_mapping(inventory_df: pd.DataFrame) -> dict:
    mapping: dict = {"links": {}, "nodes": {}, "ramais": {}, "zones": {}, "support": {}, "unknown": {}}
    counters = defaultdict(int)
    for _, row in inventory_df.iterrows():
        group = str(row.get("model_group", "UNKNOWN")).lower()
        owner = row.get("owner") or row.get("OWNER")
        table = row.get("table_name") or row.get("TABLE_NAME")
        geom = row.get("geometry_column") or row.get("GEOMETRY_COLUMN")
        source = f"{owner}.{table}"
        safe_name = _safe_layer_name(str(table))
        counters[safe_name] += 1
        if counters[safe_name] > 1:
            safe_name = f"{safe_name}_{counters[safe_name]}"
        base = {
            "source": source,
            "geometry_column": geom,
            "crs_epsg": int(row["srid"]) if str(row.get("srid", "")).isdigit() else None,
            "id_field": _first(row.get("possible_id_fields")),
            "status_field": _first(row.get("possible_status_fields")),
            "entity_type": safe_name,
            "include": False,
            "auto_classification": row.get("model_group", "UNKNOWN"),
            "note": "Confirmar manualmente antes de incluir no pipeline.",
        }
        if group == "link":
            base.update({
                "diameter_field": _first(row.get("possible_diameter_fields")),
                "material_field": _first(row.get("possible_material_fields")),
                "length_field": None,
                "system_type_field": _first(row.get("possible_network_type_fields")),
                "upstream_node_field": None,
                "downstream_node_field": None,
                "force_main": False,
            })
            mapping["links"][safe_name] = base
        elif group == "node":
            base.update({
                "cover_level_field": _first_match(row.get("possible_elevation_fields"), ["TAMPA"]),
                "invert_level_field": _first_match(row.get("possible_elevation_fields"), ["SOLEIRA", "INVERT"]),
                "ground_level_field": None,
                "node_type_field": None,
                "system_type_field": _first(row.get("possible_network_type_fields")),
            })
            mapping["nodes"][safe_name] = base
        elif group == "zone":
            base.update({"name_field": None})
            mapping["zones"][safe_name] = base
        elif group == "support":
            mapping["support"][safe_name] = base
        else:
            mapping["unknown"][safe_name] = base
    return mapping


def build_inventory_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["source_layer", "geometry_type", "srid", "record_count"])
    cols = [c for c in ["source_layer", "geometry_type", "srid", "record_count"] if c in df.columns]
    return df[cols].copy()


def _first(value: Any) -> str | None:
    if value is None or pd.isna(value) or value == "":
        return None
    return str(value).split(";")[0] or None


def _first_match(value: Any, hints: list[str]) -> str | None:
    if value is None or pd.isna(value):
        return None
    fields = str(value).split(";")
    for field in fields:
        if any(h in field for h in hints):
            return field
    return _first(value)


def _safe_layer_name(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
