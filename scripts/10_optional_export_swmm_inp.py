from __future__ import annotations

from pathlib import Path

from _bootstrap import ROOT


def main() -> int:
    Path(ROOT, "outputs", "exports").mkdir(parents=True, exist_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
