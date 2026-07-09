from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RunContext:
    run_id: str
    domain: str
    root: Path
    exports_dir: Path
    errors_dir: Path
    reports_dir: Path
    logs_dir: Path


def create_run_context(outputs_root: str | Path, domain: str) -> RunContext:
    safe_domain = domain.lower().replace(" ", "_")
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_domain}"
    root = Path(outputs_root) / "runs" / run_id
    ctx = RunContext(
        run_id=run_id,
        domain=domain,
        root=root,
        exports_dir=root / "exports",
        errors_dir=root / "erros",
        reports_dir=root / "relatorios",
        logs_dir=root / "logs",
    )
    for folder in [ctx.exports_dir, ctx.errors_dir, ctx.reports_dir, ctx.logs_dir]:
        folder.mkdir(parents=True, exist_ok=True)
    return ctx
