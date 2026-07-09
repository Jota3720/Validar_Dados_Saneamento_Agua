from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import pandas as pd

from .io import write_csv, write_excel


@dataclass
class ErrorRecord:
    error_id: str
    regra_id: str
    categoria: str
    tipo_erro: str
    gravidade: str
    source_layer: str | None
    source_id: str | int | None
    related_layer: str | None = None
    related_id: str | int | None = None
    tolerancia_m: float | None = None
    descricao: str | None = None
    acao_sugerida: str | None = None
    data_execucao: str | None = None
    confidence: str | None = None
    falso_positivo_possivel: str | None = None
    geometry_wkt: str | None = None


def records_to_frame(records: Iterable[ErrorRecord]) -> pd.DataFrame:
    return pd.DataFrame([asdict(r) for r in records])


def write_report_tables(df: pd.DataFrame, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(df, out / "resumo_erros_por_regra.csv")
    write_excel(df, out / "resumo_erros_por_regra.xlsx")
