from __future__ import annotations

from pathlib import Path


def latest_run(outputs_root: str | Path = "outputs", domain_contains: str | None = None) -> Path:
    root = Path(outputs_root) / "runs"
    if not root.exists():
        raise FileNotFoundError(f"Ainda não existem runs em {root}")
    runs = [p for p in root.iterdir() if p.is_dir()]
    if domain_contains:
        marker = domain_contains.lower()
        runs = [p for p in runs if marker in p.name.lower()]
    if not runs:
        raise FileNotFoundError(f"Não encontrei runs em {root}")
    return sorted(runs, key=lambda p: p.stat().st_mtime, reverse=True)[0]
