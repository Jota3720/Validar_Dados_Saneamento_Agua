from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shapely.geometry import LineString, Point, base
from shapely import wkt


@dataclass(frozen=True)
class CrsCheckResult:
    crs: str | None
    is_projected: bool
    is_metric: bool


def geometry_from_wkt(value: str | None):
    if value in (None, ""):
        return None
    return wkt.loads(value)


def is_empty_geometry(geom: base.BaseGeometry | None) -> bool:
    return geom is None or geom.is_empty


def is_valid_geometry(geom: base.BaseGeometry | None) -> bool:
    return geom is not None and geom.is_valid


def line_length_m(geom: base.BaseGeometry | None) -> float | None:
    if geom is None or geom.is_empty:
        return None
    if not isinstance(geom, LineString):
        return None
    return float(geom.length)


def endpoint_points(geom: base.BaseGeometry) -> tuple[Point, Point]:
    if not isinstance(geom, LineString):
        raise TypeError("endpoint_points expects a LineString")
    coords = list(geom.coords)
    return Point(coords[0]), Point(coords[-1])


def iter_points(geom: base.BaseGeometry) -> Iterable[Point]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Point):
        return [geom]
    if hasattr(geom, "geoms"):
        pts = []
        for g in geom.geoms:
            pts.extend(iter_points(g))
        return pts
    return []
