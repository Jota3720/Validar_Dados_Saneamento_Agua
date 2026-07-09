from __future__ import annotations

import argparse

from src.config_loader import load_yaml
from src.extraction import extract_layers
from src.pipeline import resolve_path
from src.run_context import create_run_context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extrai layers Oracle em modo read-only para CSV local.")
    parser.add_argument("--config", default="config/project.yaml")
    args = parser.parse_args(argv)

    config_path = resolve_path(args.config)
    cfg = load_yaml(config_path)
    domain = cfg.get("domain", "SANEAMENTO")
    outputs_root = resolve_path(cfg.get("outputs_root", "outputs"))
    ctx = create_run_context(outputs_root, domain)
    summary = extract_layers(config_path, ctx.root)
    print(f"Run criada em: {ctx.root}")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
