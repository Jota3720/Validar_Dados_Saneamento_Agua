from __future__ import annotations

from pathlib import Path

from scripts._bootstrap import ROOT


def main() -> int:
    Path(ROOT, "outputs", "erros").mkdir(parents=True, exist_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
