from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts._bootstrap import ROOT
from src.io import write_csv, write_excel


def main() -> int:
    out_dir = Path(ROOT) / "outputs" / "relatorios"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{"status": "relatorio_preparado"}])
    write_csv(df, out_dir / "resumo_erros_por_regra.csv")
    write_excel(df, out_dir / "resumo_erros_por_regra.xlsx")
    (out_dir / "relatorio_validacao_saneamento.md").write_text("# Relatorio\n\nRelatorio preparado.\n", encoding="utf-8")
    (out_dir / "relatorio_validacao_saneamento.html").write_text("<html><body><h1>Relatorio</h1></body></html>", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
