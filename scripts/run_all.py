from __future__ import annotations

import argparse

from src.pipeline import run_full_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa a pipeline completa de validação de saneamento.")
    parser.add_argument("--config", default="config/project.yaml")
    parser.add_argument("--skip-extract", action="store_true", help="Não liga à Oracle; usa exports/raw já existentes na run.")
    args = parser.parse_args(argv)
    run_dir = run_full_pipeline(args.config, domain_default="SANEAMENTO", skip_extract=args.skip_extract)
    print(f"Run criada em: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
