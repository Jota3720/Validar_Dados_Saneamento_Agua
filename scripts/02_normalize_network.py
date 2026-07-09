from __future__ import annotations

import argparse
from pathlib import Path

from src.config_loader import load_yaml
from src.normalization import normalize_raw_exports
from src.pipeline import resolve_path
from src.run_finder import latest_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normaliza exports/raw para schema comum de rede.")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--run-dir", default=None)
    args = parser.parse_args(argv)

    cfg = load_yaml(resolve_path(args.config))
    domain = cfg.get("domain", "SANEAMENTO")
    run_dir = Path(args.run_dir) if args.run_dir else latest_run(resolve_path(cfg.get("outputs_root", "outputs")), domain.lower())
    df = normalize_raw_exports(run_dir, domain=domain)
    print(f"Normalização concluída em: {run_dir}")
    print(f"Entidades normalizadas: {len(df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
