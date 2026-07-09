from __future__ import annotations

from pathlib import Path

import pandas as pd

from _bootstrap import ROOT
from src.io import write_csv


def main() -> int:
    out_dir = Path(ROOT) / "outputs" / "erros"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(pd.DataFrame(columns=["regra_id", "source_layer", "source_id", "tipo_erro"]), out_dir / "SAN_GEO_001.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
