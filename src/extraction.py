from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.config_loader import load_yaml
from src.io import write_csv, write_excel
from src.layer_mapping import load_layer_entries

SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_#$]*(\.[A-Za-z][A-Za-z0-9_#$]*)?$")


def _resolve_path(root: Path, path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def _validate_identifier(value: str, *, what: str) -> str:
    if not SAFE_IDENTIFIER_RE.match(value):
        raise ValueError(f"Identificador inseguro em {what}: {value!r}")
    return value


def _split_source(source: str, default_schema: str | None = None) -> tuple[str | None, str]:
    parts = source.split(".")
    if len(parts) == 2:
        return parts[0].upper(), parts[1].upper()
    if len(parts) == 1:
        return default_schema.upper() if default_schema else None, parts[0].upper()
    raise ValueError(f"Source inválido: {source!r}")


def _connect_oracle(database_config: dict[str, Any]):
    try:
        import oracledb
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("A dependência 'oracledb' é necessária para extrair da Oracle.") from exc

    oracle = database_config.get("oracle", {}) or {}
    user = oracle.get("user")
    password = oracle.get("password")
    dsn = oracle.get("dsn")
    if not user or not password or not dsn:
        raise ValueError("config/database.yaml tem de conter oracle.user, oracle.password e oracle.dsn")
    return oracledb.connect(user=user, password=password, dsn=dsn)


def _get_table_columns(conn, source: str, geometry_column: str, default_schema: str | None) -> list[str]:
    schema, table = _split_source(source, default_schema)
    sql = """
        SELECT column_name
        FROM all_tab_columns
        WHERE table_name = :table_name
          AND (:owner_name IS NULL OR owner = :owner_name)
        ORDER BY column_id
    """
    params = {"table_name": table.upper(), "owner_name": schema.upper() if schema else None}
    df = pd.read_sql(sql, conn, params=params)
    col_name = "COLUMN_NAME" if "COLUMN_NAME" in df.columns else "column_name"
    cols = [str(v).upper() for v in df[col_name].tolist()]
    geom_upper = geometry_column.upper()
    return [c for c in cols if c != geom_upper]


def _build_select_sql(
    *,
    source: str,
    geometry_column: str,
    columns: list[str],
    row_limit: int | None = None,
    where: str | None = None,
) -> str:
    _validate_identifier(source, what="source")
    _validate_identifier(geometry_column, what="geometry_column")
    selected = [f't."{col}" AS "{col}"' for col in columns]
    selected.append(f"SDO_UTIL.TO_WKTGEOMETRY(t.{geometry_column}) AS geometry_wkt")
    sql = f"SELECT {', '.join(selected)} FROM {source} t"
    if where:
        # O where vem do config local do projecto; não aceitar ';' evita comandos compostos.
        if ";" in where:
            raise ValueError("WHERE inseguro: não pode conter ';'")
        sql += f" WHERE {where}"
    if row_limit:
        if where:
            sql += f" AND ROWNUM <= {int(row_limit)}"
        else:
            sql += f" WHERE ROWNUM <= {int(row_limit)}"
    return sql


def extract_layers(project_config_path: str | Path, run_dir: str | Path) -> pd.DataFrame:
    """Extract configured Oracle layers to local raw CSV files.

    The function performs SELECT-only reads. It writes one CSV per enabled layer
    under `<run_dir>/exports/raw/` and a summary under `<run_dir>/relatorios/`.
    """

    project_config_path = Path(project_config_path)
    root = project_config_path.resolve().parents[1]
    cfg = load_yaml(project_config_path)
    database_config_path = _resolve_path(root, cfg.get("database_config", "config/database.yaml"))
    layers_mapping_path = _resolve_path(root, cfg.get("layers_mapping"))
    database_config = load_yaml(database_config_path)
    default_schema = (database_config.get("oracle", {}) or {}).get("schema")
    row_limit = (cfg.get("extraction", {}) or {}).get("row_limit")

    entries = load_layer_entries(layers_mapping_path)
    run_dir = Path(run_dir)
    raw_dir = run_dir / "exports" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = run_dir / "relatorios"
    reports_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    conn = _connect_oracle(database_config)
    try:
        for entry in entries:
            alias = entry["alias"]
            source = entry["source"]
            geometry_column = entry.get("geometry_column", "GEOMETRY")
            try:
                columns = _get_table_columns(conn, source, geometry_column, default_schema)
                where = (entry.get("raw", {}) or {}).get("where")
                sql = _build_select_sql(
                    source=source,
                    geometry_column=geometry_column,
                    columns=columns,
                    row_limit=row_limit,
                    where=where,
                )
                df = pd.read_sql(sql, conn)
                df.columns = [str(c).lower() for c in df.columns]
                df["_mapping_group"] = entry["group"]
                df["_mapping_alias"] = alias
                df["_source_layer"] = source
                df["_model_group"] = entry.get("model_group")
                df["_id_field"] = str(entry.get("id_field", "IPID")).lower()
                out_path = raw_dir / f"{alias}.csv"
                write_csv(df, out_path)
                rows.append(
                    {
                        "alias": alias,
                        "source_layer": source,
                        "model_group": entry.get("model_group"),
                        "status": "ok",
                        "records": len(df),
                        "output": str(out_path),
                        "error": "",
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "alias": alias,
                        "source_layer": source,
                        "model_group": entry.get("model_group"),
                        "status": "erro",
                        "records": 0,
                        "output": "",
                        "error": str(exc),
                    }
                )
    finally:
        conn.close()

    summary = pd.DataFrame(rows)
    write_csv(summary, reports_dir / "extracao_layers.csv")
    write_excel(summary, reports_dir / "extracao_layers.xlsx")
    return summary
