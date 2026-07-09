from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


def normalize_links(layers: dict[str, gpd.GeoDataFrame], mapping: dict) -> gpd.GeoDataFrame:
    frames = []
    for layer_name, gdf in layers.items():
        cfg = mapping[layer_name]
        out = gpd.GeoDataFrame(geometry=gdf.geometry, crs=gdf.crs)
        out["source_layer"] = layer_name
        out["source_id"] = _field(gdf, cfg.get("id_field"))
        out["entity_type"] = cfg.get("entity_type", layer_name)
        out["model_group"] = "LINK"
        out["status"] = _field(gdf, cfg.get("status_field"))
        out["diameter_mm"] = pd.to_numeric(_field(gdf, cfg.get("diameter_field")), errors="coerce")
        out["material"] = _field(gdf, cfg.get("material_field"))
        out["length_m"] = gdf.geometry.length
        out["entity_code"] = _field(gdf, cfg.get("entity_code_field"))
        out["parent_entity_code"] = _field(gdf, cfg.get("parent_entity_code_field"))
        out["upstream_node_id"] = _field(gdf, cfg.get("upstream_node_field"))
        out["downstream_node_id"] = _field(gdf, cfg.get("downstream_node_field"))
        out["system_type"] = _field(gdf, cfg.get("system_type_field")).fillna("desconhecido")
        out["system"] = _field(gdf, cfg.get("system_field"))
        out["subsystem"] = _field(gdf, cfg.get("subsystem_field"))
        out["basin"] = _field(gdf, cfg.get("basin_field"))
        out["zmc"] = _field(gdf, cfg.get("zmc_field"))
        _assign_optional_fields(
            out,
            gdf,
            {
                "arruamento": ["ARRUAMENTO"],
                "freguesia_caop_2012": ["FREGUESIA_CAOP_2012"],
                "freguesia_caop_2017": ["FREGUESIA_CAOP_2017"],
                "numero_policia": ["NUMERO_DE_POLICIA", "NPOLICIA", "NUMERO_POLICIA", "NP"],
            },
        )
        out["pressure_service_bar"] = pd.to_numeric(_field(gdf, cfg.get("pressure_field")), errors="coerce")
        out["pressure_nominal_bar"] = pd.to_numeric(_field(gdf, cfg.get("pressure_nominal_field")), errors="coerce")
        out["slope_percent"] = pd.to_numeric(_field(gdf, cfg.get("slope_field")), errors="coerce")
        out["regime"] = _field(gdf, cfg.get("regime_field"))
        out["burial_depth_m"] = pd.to_numeric(_field(gdf, cfg.get("burial_depth_field")), errors="coerce")
        out["force_main"] = bool(cfg.get("force_main", False))
        out["include_in_model"] = bool(cfg.get("include_in_model", True))
        frames.append(out)
    return _concat(frames)


def normalize_nodes(layers: dict[str, gpd.GeoDataFrame], mapping: dict) -> gpd.GeoDataFrame:
    frames = []
    for layer_name, gdf in layers.items():
        cfg = mapping[layer_name]
        out = gpd.GeoDataFrame(geometry=gdf.geometry, crs=gdf.crs)
        out["source_layer"] = layer_name
        out["source_id"] = _field(gdf, cfg.get("id_field"))
        out["entity_type"] = cfg.get("entity_type", layer_name)
        out["model_group"] = "NODE"
        out["status"] = _field(gdf, cfg.get("status_field"))
        out["cover_level"] = pd.to_numeric(_field(gdf, cfg.get("cover_level_field")), errors="coerce")
        out["invert_level"] = pd.to_numeric(_field(gdf, cfg.get("invert_level_field")), errors="coerce")
        out["ground_level"] = pd.to_numeric(_field(gdf, cfg.get("ground_level_field")), errors="coerce")
        out["node_type"] = _field(gdf, cfg.get("node_type_field")).fillna(cfg.get("entity_type", layer_name))
        out["system_type"] = _field(gdf, cfg.get("system_type_field")).fillna("desconhecido")
        out["system"] = _field(gdf, cfg.get("system_field"))
        out["subsystem"] = _field(gdf, cfg.get("subsystem_field"))
        out["basin"] = _field(gdf, cfg.get("basin_field"))
        out["zmc"] = _field(gdf, cfg.get("zmc_field"))
        out["entity_code"] = _field(gdf, cfg.get("entity_code_field"))
        out["parent_entity_code"] = _field(gdf, cfg.get("parent_entity_code_field"))
        _assign_optional_fields(
            out,
            gdf,
            {
                "arruamento": ["ARRUAMENTO"],
                "freguesia_caop_2012": ["FREGUESIA_CAOP_2012"],
                "freguesia_caop_2017": ["FREGUESIA_CAOP_2017"],
                "numero_policia": ["NUMERO_DE_POLICIA", "NPOLICIA", "NUMERO_POLICIA", "NP"],
            },
        )
        out["include_in_model"] = bool(cfg.get("include_in_model", True))
        frames.append(out)
    return _concat(frames)


def _field(gdf: gpd.GeoDataFrame, field: str | None):
    if field and field in gdf.columns:
        return gdf[field]
    return pd.Series([None] * len(gdf), index=gdf.index)


def _assign_optional_fields(out: gpd.GeoDataFrame, gdf: gpd.GeoDataFrame, field_map: dict[str, list[str]]) -> None:
    for out_field, candidates in field_map.items():
        series = _first_existing_field(gdf, candidates)
        if series is not None:
            out[out_field] = series


def _first_existing_field(gdf: gpd.GeoDataFrame, candidates: list[str]):
    for field in candidates:
        if field in gdf.columns:
            return gdf[field]
    return None


def _concat(frames: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    if not frames:
        return gpd.GeoDataFrame(geometry=[])
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=frames[0].crs)
