from __future__ import annotations

import argparse
from pathlib import Path

from scripts._bootstrap import ROOT
from src.config_loader import load_yaml
from src.io import write_csv, write_excel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_yaml(args.config)
    out_dir = Path(ROOT) / "outputs" / "relatorios"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"status": "inventario_preparado", "config": str(args.config), "database": cfg.get("oracle", {}).get("dsn", "")}
    write_csv(__import__("pandas").DataFrame([summary]), out_dir / "inventario_bd.csv")
    write_excel(__import__("pandas").DataFrame([summary]), out_dir / "inventario_bd.xlsx")
    (out_dir / "inventario_bd.md").write_text("# Inventario da BD\n\nInventario preparado. Confirmar layers e campos no mapping.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
