from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd

from .config_loader import load_yaml


WRITE_KEYWORDS = __import__("re").compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|CREATE|TRUNCATE|GRANT|REVOKE|COMMIT|ROLLBACK)\b",
    __import__("re").IGNORECASE,
)


def assert_read_only_sql(sql: str) -> None:
    if WRITE_KEYWORDS.search(sql):
        raise PermissionError("SQL bloqueado: o pipeline so permite consultas SELECT/read-only.")


@contextmanager
def oracle_connection(config_path: str = "config/database.yaml") -> Iterator:
    import oracledb

    cfg = load_yaml(config_path)["oracle"]
    init_error: Exception | None = None
    if cfg.get("thick_mode"):
        init_kwargs = {}
        if cfg.get("lib_dir"):
            init_kwargs["lib_dir"] = cfg["lib_dir"]
        if cfg.get("config_dir"):
            init_kwargs["config_dir"] = cfg["config_dir"]
        try:
            oracledb.init_oracle_client(**init_kwargs)
        except Exception as exc:
            if "already initialized" not in str(exc).lower():
                init_error = exc
    kwargs = {"user": cfg["user"], "password": cfg["password"], "dsn": _resolve_dsn(cfg, oracledb)}
    if cfg.get("config_dir"):
        kwargs["config_dir"] = cfg["config_dir"]
    try:
        conn = oracledb.connect(**kwargs)
    except Exception as connect_exc:
        if init_error is not None:
            raise connect_exc from init_error
        raise
    try:
        yield conn
    finally:
        conn.close()


def read_sql(conn, sql: str, params: dict | None = None) -> pd.DataFrame:
    assert_read_only_sql(sql)
    return pd.read_sql(sql, conn, params=params or {})


def spatial_inventory(conn, schemas: list[str] | None = None, table_like: str = "%") -> pd.DataFrame:
    owner_filter = ""
    params = {"table_like": table_like.upper()}
    if schemas:
        owner_filter = "AND m.owner IN ({})".format(",".join(f":owner_{i}" for i in range(len(schemas))))
        params.update({f"owner_{i}": s.upper() for i, s in enumerate(schemas)})
    sql = f"""
        SELECT
            m.owner,
            m.table_name,
            m.column_name AS geometry_column,
            m.srid,
            o.object_type
        FROM all_sdo_geom_metadata m
        LEFT JOIN all_objects o
          ON o.owner = m.owner
         AND o.object_name = m.table_name
         AND o.object_type IN ('TABLE', 'VIEW')
        WHERE UPPER(m.table_name) LIKE :table_like
        {owner_filter}
        ORDER BY m.owner, m.table_name, m.column_name
    """
    return read_sql(conn, sql, params)


def count_rows(conn, owner: str, table_name: str) -> int | None:
    sql = f'SELECT COUNT(*) AS N FROM "{owner}"."{table_name}"'
    try:
        return int(read_sql(conn, sql).iloc[0]["N"])
    except Exception:
        return None


def list_columns(conn, owner: str, table_name: str) -> pd.DataFrame:
    sql = """
        SELECT column_name, data_type, data_length, nullable
        FROM all_tab_columns
        WHERE owner = :owner AND table_name = :table_name
        ORDER BY column_id
    """
    return read_sql(conn, sql, {"owner": owner.upper(), "table_name": table_name.upper()})


def detect_geometry_type(conn, owner: str, table_name: str, geom_col: str, sample_rows: int = 25) -> str | None:
    sql = f"""
        SELECT DISTINCT SDO_GTYPE AS GTYPE
        FROM (
            SELECT t."{geom_col}".SDO_GTYPE AS SDO_GTYPE
            FROM "{owner}"."{table_name}" t
            WHERE t."{geom_col}" IS NOT NULL
              AND ROWNUM <= :sample_rows
        )
    """
    try:
        values = read_sql(conn, sql, {"sample_rows": sample_rows})["GTYPE"].dropna().astype(int).tolist()
    except Exception:
        return None
    names = sorted({_oracle_gtype_name(v) for v in values})
    return ", ".join(names) if names else None


def _oracle_gtype_name(gtype: int) -> str:
    kind = gtype % 10
    return {
        1: "POINT",
        2: "LINESTRING",
        3: "POLYGON",
        5: "MULTIPOINT",
        6: "MULTILINESTRING",
        7: "MULTIPOLYGON",
    }.get(kind, f"SDO_GTYPE_{gtype}")


def _resolve_dsn(cfg: dict, oracledb) -> str:
    dsn = cfg.get("dsn")
    if dsn:
        return str(dsn)
    host = cfg.get("host")
    port = int(cfg.get("port", 1521))
    service_name = cfg.get("service_name") or cfg.get("service")
    sid = cfg.get("sid")
    if host and service_name:
        return oracledb.makedsn(str(host), port, service_name=str(service_name))
    if host and sid:
        return oracledb.makedsn(str(host), port, sid=str(sid))
    raise ValueError("Config Oracle invalida: defina dsn ou host + service_name/sid.")


# Legacy compatibility for the previous simplified clone
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class DatabaseConfig:
    user: str
    password: str
    dsn: str
    schema: str | None = None


class OracleReadOnlyClient:
    def __init__(self, config_path: str | Path):
        cfg = load_yaml(config_path).get("oracle", {})
        self.config = DatabaseConfig(
            user=cfg.get("user", ""),
            password=cfg.get("password", ""),
            dsn=cfg.get("dsn", ""),
            schema=cfg.get("schema"),
        )
        if not self.config.user or not self.config.password or not self.config.dsn:
            raise ValueError("Database config missing user/password/dsn")
        self._engine = create_engine(
            f"oracle+oracledb://{self.config.user}:{self.config.password}@{self.config.dsn}",
            pool_pre_ping=True,
        )

    def query_df(self, sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        with self._engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)

    def close(self) -> None:
        self._engine.dispose()
