from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from src.config_loader import load_yaml


LayerEntry = dict[str, Any]


def iter_layer_entries(mapping: dict[str, Any]) -> Iterator[LayerEntry]:
    """Yield enabled layer definitions from the nested mapping YAML.

    Output keys are normalised enough for the rest of the pipeline, while keeping
    the original mapping values available.
    """

    for group_name, group_cfg in (mapping or {}).items():
        if not isinstance(group_cfg, dict):
            continue
        for alias, cfg in group_cfg.items():
            if not isinstance(cfg, dict):
                continue
            if cfg.get("include", True) is False:
                continue
            source = cfg.get("source")
            if not source:
                continue
            yield {
                "group": group_name,
                "alias": alias,
                "source": source,
                "geometry_column": cfg.get("geometry_column", "GEOMETRY"),
                "id_field": cfg.get("id_field", "IPID"),
                "model_group": cfg.get("model_group", group_name.upper()),
                "note": cfg.get("note", ""),
                "raw": cfg,
            }


def load_layer_entries(path: str | Path) -> list[LayerEntry]:
    return list(iter_layer_entries(load_yaml(path)))
