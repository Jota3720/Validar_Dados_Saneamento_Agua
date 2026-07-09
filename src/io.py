from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config_loader import project_path


LOG = logging.getLogger(__name__)


def setup_logging(log_path: str | Path | None = None, level: int = logging.INFO) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_path:
        p = project_path(log_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(p, encoding="utf-8"))
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s", handlers=handlers, force=True)


def ensure_parent(path: str | Path) -> Path:
    p = project_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = ensure_parent(path)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def write_excel(df: pd.DataFrame, path: str | Path, sheet_name: str = "Sheet1") -> None:
    p = ensure_parent(path)
    with pd.ExcelWriter(p, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)


def write_table(df: pd.DataFrame, path: str | Path) -> Path:
    p = ensure_parent(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        df.to_csv(p, index=False, encoding="utf-8-sig")
    elif suffix in {".xlsx", ".xls"}:
        df.to_excel(p, index=False)
    elif suffix in {".md", ".markdown"}:
        p.write_text(df.to_markdown(index=False), encoding="utf-8")
    else:
        raise ValueError(f"Formato de tabela nao suportado: {p}")
    LOG.info("Escrito %s", p)
    return p


def read_layer(path: str | Path, layer: str | None = None):
    import geopandas as gpd

    p = project_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Layer local nao encontrada: {p}")
    return gpd.read_file(p, layer=layer)


def write_gdf(gdf, path: str | Path, layer: str | None = None) -> Path:
    import geopandas as gpd  # noqa: F401

    p = project_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() == ".gpkg" and p.exists():
        p.unlink()
        for extra in [p.with_name(p.name + "-journal"), p.with_name(p.name + "-wal"), p.with_name(p.name + "-shm")]:
            if extra.exists():
                try:
                    extra.unlink()
                except Exception:
                    pass
    if p.suffix.lower() == ".shp":
        gdf.to_file(p, engine="pyogrio")
    else:
        gdf.to_file(p, layer=layer or p.stem, driver="GPKG", engine="pyogrio")
    LOG.info("Escrito %s registos em %s", len(gdf), p)
    return p
