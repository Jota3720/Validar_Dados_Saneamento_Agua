from __future__ import annotations

from math import isfinite
from typing import Iterable

import pandas as pd

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


def _endpoints(geom) -> list:
    if geom is None or getattr(geom, "is_empty", False):
        return []
    try:
        geom_type = getattr(geom, "geom_type", "")
        if geom_type == "LineString":
            coords = list(geom.coords)
            if len(coords) < 2:
                return []
            from shapely.geometry import Point

            return [Point(coords[0]), Point(coords[-1])]
        if geom_type == "MultiLineString":
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


def _has_near_geometry(point, candidates: pd.DataFrame, tolerance: float) -> bool:
    for _, geom in _iter_geoms(candidates):
        distance = _safe_distance(point, geom)
        if distance is not None and distance <= tolerance:
            return True
    return False


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
    """Validate minimum link/node connectivity using geometric tolerance.

    This is intentionally conservative. It does not mutate input data and does not
    replace a full graph validation, but it already catches the most common class
    of topological errors: dangling link endpoints and isolated nodes.
    """

    tolerance = float(tolerances.get("near_tolerance_m", tolerances.get("snap_tolerance_m", 0.20)) or 0.20)
    issues = []

    if links.empty and nodes.empty:
        return normalize_issues(pd.DataFrame(), domain=domain, run_id=run_id, default_theme="TOPOLOGIA")

    for _, node in nodes.iterrows():
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
                    geometry_wkt=_to_wkt(node.get("geometry")),
                    run_id=run_id,
                )
            )

    for _, link in links.iterrows():
        geom = link.get("geometry")
        endpoints = _endpoints(geom)
        if not endpoints:
            continue
        for endpoint in endpoints:
            connected_to_node = _has_near_geometry(endpoint, nodes, tolerance)
            connected_to_link = False
            if allow_link_link_endpoint_connections:
                other_links = links[links.index != link.name] if link.name in links.index else links
                connected_to_link = _has_near_geometry(endpoint, other_links, tolerance)
            if not connected_to_node and not connected_to_link:
                issues.append(
                    make_issue(
                        regra_id=f"{code_prefix}_TOPO_001",
                        message=f"Extremidade de {link_term} sem nó associado dentro da tolerância",
                        domain=domain,
                        theme="TOPOLOGIA",
                        severity="CRITICA",
                        source_layer=source_layer_alias or link.get("source_layer"),
                        source_id=link.get("source_id"),
                        model_group=link.get("model_group", "LINK"),
                        entity_type=link.get("entity_type"),
                        suggested_fix="Corrigir snap entre link e nó, criar nó em falta ou ajustar tolerância se justificado.",
                        geometry_wkt=_to_wkt(endpoint),
                        run_id=run_id,
                    )
                )

    for _, node in _iter_geoms(nodes):
        if not _has_near_geometry(node.get("geometry"), links, tolerance):
            issues.append(
                make_issue(
                    regra_id=f"{code_prefix}_TOPO_002",
                    message="Nó isolado sem link associado dentro da tolerância",
                    domain=domain,
                    theme="TOPOLOGIA",
                    severity="ALTA",
                    source_layer=node.get("source_layer"),
                    source_id=node.get("source_id"),
                    model_group=node.get("model_group", "NODE"),
                    entity_type=node.get("entity_type"),
                    suggested_fix="Confirmar se é cadastro abandonado, nó solto ou erro de snap.",
                    geometry_wkt=_to_wkt(node.get("geometry")),
                    run_id=run_id,
                )
            )

    return normalize_issues(pd.DataFrame(issues), domain=domain, run_id=run_id, default_theme="TOPOLOGIA")
