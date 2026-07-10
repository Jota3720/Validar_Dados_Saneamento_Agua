from __future__ import annotations

from math import isfinite
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString, Point

from src.issue_schema import make_issue, normalize_issues


def _safe_distance(a, b) -> float | None:
    if a is None or b is None:
        return None
    try:
        value = a.distance(b)
    except Exception:
        return None
    return float(value) if isfinite(float(value)) else None


def _to_wkt(geom) -> str | None:
    return getattr(geom, "wkt", None) if geom is not None else None


def _endpoints(geom) -> list[Point]:
    if geom is None or getattr(geom, "is_empty", False):
        return []
    try:
        if isinstance(geom, LineString):
            coords = list(geom.coords)
            if len(coords) < 2:
                return []
            return [Point(coords[0]), Point(coords[-1])]
        if isinstance(geom, MultiLineString):
            pts = []
            for part in geom.geoms:
                pts.extend(_endpoints(part))
            return pts
        boundary = getattr(geom, "boundary", None)
        if boundary is not None and not getattr(boundary, "is_empty", False):
            if getattr(boundary, "geom_type", "") == "MultiPoint":
                return list(boundary.geoms)
            if getattr(boundary, "geom_type", "") == "Point":
                return [boundary]
    except Exception:
        return []
    return []


def _iter_geoms(df: pd.DataFrame) -> Iterable[tuple[pd.Series, object]]:
    for _, row in df.iterrows():
        geom = row.get("geometry")
        if geom is not None and not getattr(geom, "is_empty", False):
            yield row, geom


def _nearby_features(gdf: gpd.GeoDataFrame, geom, tolerance_m: float) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf.iloc[0:0]
    try:
        idx = list(gdf.sindex.query(geom.buffer(tolerance_m), predicate="intersects"))
        if idx:
            return gdf.iloc[idx]
    except Exception:
        pass
    try:
        mask = gdf.geometry.distance(geom) <= tolerance_m
        return gdf.loc[mask]
    except Exception:
        return gdf.iloc[0:0]


def _has_near_geometry(point, candidates: pd.DataFrame, tolerance: float) -> bool:
    if candidates.empty:
        return False
    if not isinstance(candidates, gpd.GeoDataFrame):
        candidates = gpd.GeoDataFrame(candidates.copy(), geometry="geometry", crs=getattr(candidates, "crs", None))
    return not _nearby_features(candidates, point, tolerance).empty


def _endpoint_touches_other_link(endpoint, links: gpd.GeoDataFrame, current_link) -> bool:
    if links.empty:
        return False
    current_id = current_link.get("source_id")
    current_layer = current_link.get("source_layer")
    candidates = _nearby_features(links, endpoint, 0.05)
    if candidates.empty:
        return False
    for _, other in candidates.iterrows():
        if other is current_link:
            continue
        if current_id is not None and other.get("source_id") == current_id and other.get("source_layer") == current_layer:
            continue
        other_geom = other.geometry
        if other_geom is None or getattr(other_geom, "is_empty", False):
            continue
        if _safe_distance(other_geom, endpoint) is not None and _safe_distance(other_geom, endpoint) <= 0.05:
            return True
        try:
            if other_geom.touches(endpoint) or other_geom.intersects(endpoint):
                return True
        except Exception:
            continue
    return False


def _link_touches_other_link(link_geom, links: gpd.GeoDataFrame, current_link) -> bool:
    start_endpoints = _endpoints(link_geom)
    return any(_endpoint_touches_other_link(endpoint, links, current_link) for endpoint in start_endpoints)


def validate_nodes_links(
    links: pd.DataFrame,
    nodes: pd.DataFrame,
    tolerances: dict,
    code_prefix: str = "SAN",
    link_term: str = "coletor",
    source_layer_alias: str | None = None,
    allow_link_link_endpoint_connections: bool = False,
    *,
    domain: str = "SANEAMENTO",
    run_id: str = "",
) -> pd.DataFrame:
    tolerance = float(tolerances.get("near_tolerance_m", tolerances.get("snap_tolerance_m", 0.20)) or 0.20)
    iso_tol = float(tolerances.get("isolation_tolerance_m", 0.50) or 0.50)
    snap_tol = float(tolerances.get("snap_tolerance_m", 0.05) or 0.05)
    issues = []

    if links.empty and nodes.empty:
        return normalize_issues(pd.DataFrame(), domain=domain, run_id=run_id, default_theme="TOPOLOGIA")

    if not isinstance(links, gpd.GeoDataFrame):
        links = gpd.GeoDataFrame(links.copy(), geometry="geometry", crs=getattr(links, "crs", None))
    if not isinstance(nodes, gpd.GeoDataFrame):
        nodes = gpd.GeoDataFrame(nodes.copy(), geometry="geometry", crs=getattr(nodes, "crs", None))

    for _, node in nodes.iterrows():
        geom = node.get("geometry")
        if geom is None or getattr(geom, "is_empty", False):
            continue
        if pd.isna(node.get("source_id")):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_ATT_001",
                    message="ID nulo",
                    domain=domain,
                    theme="ATRIBUTOS",
                    severity="ALTA",
                    source_layer=node.get("source_layer"),
                    source_id=None,
                    model_group=node.get("model_group", "NODE"),
                    entity_type=node.get("entity_type"),
                    suggested_fix="Preencher IPID/identificador antes de validar topologia.",
                    geometry_wkt=_to_wkt(geom),
                    run_id=run_id,
                )
            )
        dist = _nearest_distance(geom, links)
        connected = _has_near_geometry(geom, links, snap_tol)
        if not connected:
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_TOPO_001",
                    message=f"No nao toca em nenhuma {link_term}",
                    domain=domain,
                    theme="TOPOLOGIA",
                    severity="ALTA",
                    source_layer=source_layer_alias or node.get("source_layer"),
                    source_id=node.get("source_id"),
                    model_group=node.get("model_group", "NODE"),
                    entity_type=node.get("entity_type"),
                    suggested_fix=f"Corrigir snapping do no a {link_term} correta ou validar se e um falso positivo.",
                    geometry_wkt=_to_wkt(geom),
                    run_id=run_id,
                )
            )
        if dist is not None and snap_tol < dist <= tolerance:
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_TOPO_002",
                    message=f"No proximo de {link_term} mas sem tocar",
                    domain=domain,
                    theme="TOPOLOGIA",
                    severity="ALTA",
                    source_layer=source_layer_alias or node.get("source_layer"),
                    source_id=node.get("source_id"),
                    model_group=node.get("model_group", "NODE"),
                    entity_type=node.get("entity_type"),
                    suggested_fix="Corrigir snapping do no a ligacao mais proxima ou validar tolerancia.",
                    geometry_wkt=_to_wkt(geom),
                    tolerancia_m=tolerance,
                    run_id=run_id,
                )
            )
        if dist is None or dist > iso_tol:
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_TOPO_003",
                    message="No isolado",
                    domain=domain,
                    theme="TOPOLOGIA",
                    severity="ALTA",
                    source_layer=source_layer_alias or node.get("source_layer"),
                    source_id=node.get("source_id"),
                    model_group=node.get("model_group", "NODE"),
                    entity_type=node.get("entity_type"),
                    suggested_fix="Confirmar se e terminal, elemento especial ou erro de geometria.",
                    geometry_wkt=_to_wkt(geom),
                    tolerancia_m=iso_tol,
                    run_id=run_id,
                )
            )

    for _, link in links.iterrows():
        geom = link.get("geometry")
        if geom is None or getattr(geom, "is_empty", False):
            continue
        dist = _nearest_distance(geom, nodes)
        if (dist is None or dist > iso_tol) and not (
            allow_link_link_endpoint_connections and _link_touches_other_link(geom, links, link)
        ):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_TOPO_004",
                    message=f"{link_term.capitalize()} sem qualquer no proximo",
                    domain=domain,
                    theme="TOPOLOGIA",
                    severity="CRITICA",
                    source_layer=source_layer_alias or link.get("source_layer"),
                    source_id=link.get("source_id"),
                    model_group=link.get("model_group", "LINK"),
                    entity_type=link.get("entity_type"),
                    suggested_fix=f"Associar/criar nos nas extremidades ou excluir se nao for elemento modelavel.",
                    geometry_wkt=_to_wkt(geom),
                    tolerancia_m=iso_tol,
                    run_id=run_id,
                )
            )
        for pos, endpoint in [("inicial", _endpoints(geom)[0] if _endpoints(geom) else None), ("final", _endpoints(geom)[-1] if _endpoints(geom) else None)]:
            if endpoint is None:
                continue
            nearby_nodes = _nearby_features(nodes, endpoint, tolerance)
            exact_nodes = nearby_nodes[nearby_nodes.geometry.distance(endpoint) <= snap_tol] if not nearby_nodes.empty else nearby_nodes
            if nearby_nodes.empty:
                if allow_link_link_endpoint_connections and _endpoint_touches_other_link(endpoint, links, link):
                    continue
                issues.append(
                    make_issue(
                        regra_id=f"{code_prefix}_TOPO_005",
                        message=f"Extremidade de {link_term} sem no proximo",
                        domain=domain,
                        theme="TOPOLOGIA",
                        severity="CRITICA",
                        source_layer=source_layer_alias or link.get("source_layer"),
                        source_id=link.get("source_id"),
                        model_group=link.get("model_group", "LINK"),
                        entity_type=link.get("entity_type"),
                        suggested_fix=f"Verificar snapping da {link_term} ao no mais proximo ou criar/associar no correto.",
                        geometry_wkt=_to_wkt(endpoint),
                        tolerancia_m=tolerance,
                        run_id=run_id,
                    )
                )
            elif exact_nodes.empty:
                if allow_link_link_endpoint_connections and _endpoint_touches_other_link(endpoint, links, link):
                    continue
                issues.append(
                    make_issue(
                        regra_id=f"{code_prefix}_TOPO_006",
                        message="Extremidade proxima mas nao coincidente com no",
                        domain=domain,
                        theme="TOPOLOGIA",
                        severity="ALTA",
                        source_layer=source_layer_alias or link.get("source_layer"),
                        source_id=link.get("source_id"),
                        model_group=link.get("model_group", "LINK"),
                        entity_type=link.get("entity_type"),
                        suggested_fix=f"Corrigir snapping na extremidade da {link_term} ou validar excecao operacional.",
                        geometry_wkt=_to_wkt(endpoint),
                        tolerancia_m=snap_tol,
                        run_id=run_id,
                    )
                )
    return normalize_issues(pd.DataFrame(issues), domain=domain, run_id=run_id, default_theme="TOPOLOGIA")


def _nearest_distance(geom, others: gpd.GeoDataFrame) -> float | None:
    if geom is None or getattr(geom, "is_empty", False) or others.empty:
        return None
    try:
        idx = list(others.sindex.nearest(geom, return_all=False))
        if not idx or len(idx) < 2 or len(idx[1]) == 0:
            return None
        other = others.geometry.iloc[int(idx[1][0])]
        return float(geom.distance(other))
    except Exception:
        try:
            return float(others.geometry.distance(geom).min())
        except Exception:
            return None
