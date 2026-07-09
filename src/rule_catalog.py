from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config_loader import load_yaml

CATALOG_COLUMNS = [
    "regra_id",
    "domain",
    "prefix",
    "theme",
    "severity",
    "description",
    "suggested_fix",
    "output_geometry",
]


def _resolve_rule(common: dict[str, Any], rule_id: str, rule_cfg: dict[str, Any]) -> dict[str, Any]:
    base_key = rule_cfg.get("extends")
    base = common.get(base_key, {}).copy() if base_key else {}
    base.update({k: v for k, v in rule_cfg.items() if k != "extends"})
    return base


def load_rules_catalog(path: str | Path = "config/rules_catalog.yaml") -> dict[str, Any]:
    return load_yaml(path)


def flatten_rules_catalog(path: str | Path = "config/rules_catalog.yaml") -> pd.DataFrame:
    catalog = load_rules_catalog(path)
    common = catalog.get("common", {}) or {}
    rows: list[dict[str, Any]] = []

    for section in ("water", "sewer"):
        section_cfg = catalog.get(section, {}) or {}
        domain = section_cfg.get("domain", section.upper())
        prefix = section_cfg.get("prefix", section.upper())
        rules = section_cfg.get("rules", {}) or {}
        for regra_id, rule_cfg in rules.items():
            resolved = _resolve_rule(common, regra_id, rule_cfg or {})
            rows.append(
                {
                    "regra_id": regra_id,
                    "domain": domain,
                    "prefix": prefix,
                    "theme": resolved.get("theme", "GERAL"),
                    "severity": resolved.get("severity", "MEDIA"),
                    "description": resolved.get("description", ""),
                    "suggested_fix": resolved.get("suggested_fix", ""),
                    "output_geometry": resolved.get("output_geometry", "SOURCE"),
                }
            )

    return pd.DataFrame(rows, columns=CATALOG_COLUMNS)


def catalog_for_domain(path: str | Path, domain: str) -> pd.DataFrame:
    df = flatten_rules_catalog(path)
    if df.empty:
        return df
    return df[df["domain"].str.upper() == domain.upper()].reset_index(drop=True)
