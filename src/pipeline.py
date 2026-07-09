from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts._bootstrap import ROOT
from src.config_loader import load_yaml
from src.extraction import extract_layers
from src.io import write_csv, write_excel
from src.normalization import normalize_raw_exports
from src.rule_catalog import catalog_for_domain
from src.run_context import create_run_context
from src.validation_runner import validate_run


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else Path(ROOT, p)


def _write_manifest(ctx, cfg: dict, config_path: Path, rules_count: int, status: str, note: str) -> None:
    manifest = pd.DataFrame(
        [
            {
                "run_id": ctx.run_id,
                "domain": ctx.domain,
                "config": str(config_path),
                "layers_mapping": cfg.get("layers_mapping", ""),
                "tolerances": cfg.get("tolerances", ""),
                "rules_catalog": cfg.get("rules_catalog", ""),
                "rules_count": rules_count,
                "status": status,
                "note": note,
            }
        ]
    )
    write_csv(manifest, ctx.reports_dir / "manifest.csv")
    write_excel(manifest, ctx.reports_dir / "manifest.xlsx")


def run_full_pipeline(config_path: str | Path, *, domain_default: str, skip_extract: bool = False) -> Path:
    config_path = resolve_path(config_path)
    cfg = load_yaml(config_path)
    domain = cfg.get("domain", domain_default)
    outputs_root = resolve_path(cfg.get("outputs_root", "outputs"))
    ctx = create_run_context(outputs_root, domain)

    rules_path = resolve_path(cfg.get("rules_catalog", "config/rules_catalog.yaml"))
    tolerances_path = resolve_path(cfg.get("tolerances", "config/tolerancias.yaml"))
    rules = catalog_for_domain(rules_path, domain)
    write_csv(rules, ctx.reports_dir / "catalogo_regras.csv")
    write_excel(rules, ctx.reports_dir / "catalogo_regras.xlsx")

    status = "ok"
    notes: list[str] = []

    if skip_extract:
        notes.append("Extracção Oracle ignorada por opção; a pipeline espera encontrar exports/raw/*.csv existentes.")
    else:
        extraction_summary = extract_layers(config_path, ctx.root)
        failed = extraction_summary[extraction_summary["status"] != "ok"] if not extraction_summary.empty else extraction_summary
        if failed is not None and not failed.empty:
            status = "partial_extract_errors"
            notes.append(f"Extracção terminou com {len(failed)} camada(s) em erro. Ver relatorios/extracao_layers.csv.")
        else:
            notes.append("Extracção Oracle read-only concluída.")

    normalized = normalize_raw_exports(ctx.root, domain=domain)
    notes.append(f"Normalização concluída com {len(normalized)} entidade(s).")

    issues = validate_run(ctx.root, domain=domain, run_id=ctx.run_id, tolerances_path=tolerances_path)
    notes.append(f"Validação concluída com {len(issues)} erro(s).")

    _write_manifest(ctx, cfg, config_path, len(rules), status, " ".join(notes))
    (ctx.reports_dir / "README_RUN.md").write_text(
        f"# Execução {ctx.run_id}\n\n"
        f"Domínio: {domain}\n\n"
        f"Estado: {status}\n\n"
        + "\n".join(f"- {note}" for note in notes)
        + "\n\nFicheiros principais:\n"
        + "- erros/validacao_erros.csv\n"
        + "- erros/validacao_erros_legivel.xlsx\n"
        + "- relatorios/resumo_erros_por_regra.xlsx\n"
        + "- relatorios/amostra_casos_reais.xlsx\n",
        encoding="utf-8",
    )
    return ctx.root
