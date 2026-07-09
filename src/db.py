from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from .config_loader import load_yaml


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
