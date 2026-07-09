from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts._bootstrap import ROOT
from src.io import write_csv


def main() -> int:
    out_dir = Path(ROOT) / "outputs" / "erros"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(pd.DataFrame(columns=["error_id", "regra_id", "categoria", "tipo_erro"]), out_dir / "ERROS_MODELO_MASTER.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
