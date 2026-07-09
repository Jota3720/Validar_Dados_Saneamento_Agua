from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
import pandas as pd

from src.config_loader import ensure_output_dirs, load_yaml, save_yaml
from src.db import count_rows, detect_geometry_type, list_columns, oracle_connection, spatial_inventory
from src.inventory import build_layers_mapping, classify_layer, summarize_columns
from src.io import setup_logging, write_table


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventaria tabelas/views espaciais Oracle em modo read-only.")
    parser.add_argument("--config", default="config/database.yaml")
    parser.add_argument("--mapping-output", default="config/layers_mapping.yaml")
    args = parser.parse_args()

    paths = ensure_output_dirs("outputs")
    setup_logging(paths["logs"] / "00_inventory_database.log")
    cfg = load_yaml(args.config)
    oracle_cfg = cfg.get("oracle", {})
    rows = []
    try:
        with oracle_connection(args.config) as conn:
            base = spatial_inventory(
                conn,
                schemas=oracle_cfg.get("schemas"),
                table_like=oracle_cfg.get("table_name_like", "%"),
            )
            for _, item in base.iterrows():
                owner = item["OWNER"]
                table = item["TABLE_NAME"]
                geom = item["GEOMETRY_COLUMN"]
                cols = list_columns(conn, owner, table)
                summary = summarize_columns(cols)
                geometry_type = detect_geometry_type(conn, owner, table, geom, oracle_cfg.get("max_sample_rows", 25))
                row = {
                    "owner": owner,
                    "table_name": table,
                    "object_type": item.get("OBJECT_TYPE"),
                    "geometry_column": geom,
                    "geometry_type": geometry_type,
                    "srid": item.get("SRID"),
                    "record_count": count_rows(conn, owner, table),
                    **summary,
                }
                row["model_group"] = classify_layer(table, geometry_type)
                rows.append(row)
    except Exception as exc:
        error_md = paths["reports"] / "inventario_bd.md"
        error_md.write_text(
            "# Inventario da BD SIG\n\n"
            f"Falha ao ligar/inventariar a BD em modo read-only.\n\nErro: `{exc}`\n\n"
            "Confirmar config/database.yaml, credenciais, DSN, schemas e permissoes SELECT.",
            encoding="utf-8",
        )
        print(f"Falha no inventario: {exc}")
        return 2

    df = pd.DataFrame(rows)
    write_table(df, paths["reports"] / "inventario_bd.csv")
    write_table(df, paths["reports"] / "inventario_bd.xlsx")
    write_table(df, paths["reports"] / "inventario_bd.md")
    save_yaml(build_layers_mapping(df), args.mapping_output)
    print(f"Inventario concluido: {len(df)} layers espaciais.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
