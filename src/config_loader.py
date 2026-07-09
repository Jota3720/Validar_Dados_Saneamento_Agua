from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def load_yaml(path: str | Path) -> dict[str, Any]:
    p = project_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Ficheiro de configuracao nao encontrado: {p}")
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {p}")
    return data


def save_yaml(data: Any, path: str | Path) -> Path:
    p = project_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=False, sort_keys=False)
    return p


def ensure_output_dirs(outputs_root: str | Path = "outputs") -> dict[str, Path]:
    root = project_path(outputs_root)
    paths = {
        "root": root,
        "errors": root / "erros",
        "reports": root / "relatorios",
        "exports": root / "exports",
        "logs": root / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def dump_yaml(data: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)
