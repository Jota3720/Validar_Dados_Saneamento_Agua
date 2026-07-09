from __future__ import annotations

import argparse
from pathlib import Path

from scripts._bootstrap import ROOT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--database-config", required=True)
    args = parser.parse_args()
    out_dir = Path(ROOT) / "outputs" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "san_links.csv").write_text("source_layer,source_id,geometry_wkt\n", encoding="utf-8")
    (out_dir / "san_nodes.csv").write_text("source_layer,source_id,geometry_wkt\n", encoding="utf-8")
    (out_dir / "san_ramais.csv").write_text("source_layer,source_id,geometry_wkt\n", encoding="utf-8")
    (out_dir / "san_zones.csv").write_text("source_layer,source_id,geometry_wkt\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
