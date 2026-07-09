from __future__ import annotations

import argparse
from pathlib import Path

from src.config_loader import load_yaml
from src.pipeline import resolve_path
from src.run_finder import latest_run
from src.validation_runner import validate_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa validação topológica básica sobre a última run ou uma run indicada.")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--run-dir", default=None)
    args = parser.parse_args(argv)

    cfg = load_yaml(resolve_path(args.config))
    domain = cfg.get("domain", "SANEAMENTO")
    run_dir = Path(args.run_dir) if args.run_dir else latest_run(resolve_path(cfg.get("outputs_root", "outputs")), domain.lower())
    issues = validate_run(
        run_dir,
        domain=domain,
        run_id=run_dir.name,
        tolerances_path=resolve_path(cfg.get("tolerances", "config/tolerancias.yaml")),
        stages={"topology"},
    )
    print(f"Erros topológicos: {len(issues)}")
    print(f"Run: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
