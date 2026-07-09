from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

from _bootstrap import ROOT
from src.config_loader import load_yaml
from src.io import write_csv, write_excel
from src.issue_schema import empty_issues
from src.rule_catalog import catalog_for_domain
from src.run_context import create_run_context


def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else Path(ROOT, p)


def _write_manifest(ctx, cfg: dict, config_path: Path, rules_count: int) -> None:
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
                "status": "preflight_ok",
                "note": "Execução estruturada criada. A extracção Oracle e a normalização real ainda têm de ser implementadas.",
            }
        ]
    )
    write_csv(manifest, ctx.reports_dir / "manifest.csv")
    write_excel(manifest, ctx.reports_dir / "manifest.xlsx")


def run_pipeline(config_path: str | Path = "config/project_water.yaml", *, skip_extract: bool = False) -> Path:
    config_path = _resolve_path(config_path)
    cfg = load_yaml(config_path)
    domain = cfg.get("domain", "AGUA")
    outputs_root = _resolve_path(cfg.get("outputs_root", "outputs"))
    ctx = create_run_context(outputs_root, domain)
    database_config = _resolve_path(cfg.get("database_config", "config/database.yaml"))
    skip_extract = skip_extract or bool(cfg.get("skip_extract", False))

    if not skip_extract:
        _run_extraction(
            script_name="01_extract_layers_water.py",
            config_path=_resolve_path(cfg.get("layers_mapping", "config/layers_mapping_water.yaml")),
            database_config=database_config,
        )

    rules_path = _resolve_path(cfg.get("rules_catalog", "config/rules_catalog.yaml"))
    rules = catalog_for_domain(rules_path, domain)
    write_csv(rules, ctx.reports_dir / "catalogo_regras.csv")
    write_excel(rules, ctx.reports_dir / "catalogo_regras.xlsx")
    write_csv(rules, Path(ROOT) / "outputs" / "relatorios" / "catalogo_regras.csv")
    write_excel(rules, Path(ROOT) / "outputs" / "relatorios" / "catalogo_regras.xlsx")

    issues = empty_issues()
    write_csv(issues, ctx.errors_dir / "validacao_erros.csv")
    write_excel(issues, ctx.errors_dir / "validacao_erros.xlsx")
    write_csv(issues, Path(ROOT) / "outputs" / "erros" / "validacao_erros.csv")
    write_excel(issues, Path(ROOT) / "outputs" / "erros" / "validacao_erros.xlsx")

    _write_manifest(ctx, cfg, config_path, len(rules))
    (ctx.reports_dir / "README_RUN.md").write_text(
        f"# Execução {ctx.run_id}\n\n"
        f"Domínio: {domain}\n\n"
        "Esta execução cria a estrutura final esperada pelo Spatial Model/GeoMedia. "
        "Ainda não substitui a extracção Oracle nem a normalização real das layers.\n",
        encoding="utf-8",
    )
    (Path(ROOT) / "outputs" / "relatorios" / "README_RUN.md").write_text(
        (ctx.reports_dir / "README_RUN.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    write_csv(
        pd.DataFrame([{"run_id": ctx.run_id, "domain": ctx.domain, "status": "ok"}]),
        Path(ROOT) / "outputs" / "relatorios" / "manifest.csv",
    )
    return ctx.root


def _run_extraction(*, script_name: str, config_path: Path, database_config: Path) -> None:
    script = Path(ROOT) / "scripts" / script_name
    if not script.exists():
        raise FileNotFoundError(f"Script de extracao nao encontrado: {script}")
    cmd = [
        sys.executable,
        str(script),
        "--config",
        str(config_path),
        "--database-config",
        str(database_config),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(message or f"Extracao falhou com codigo {proc.returncode}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa o pipeline de validação de água em modo seguro.")
    parser.add_argument("--config", default="config/project_water.yaml")
    parser.add_argument("--skip-extract", action="store_true", help="Nao executa a extracao Oracle.")
    args = parser.parse_args(argv)
    run_dir = run_pipeline(args.config, skip_extract=args.skip_extract)
    print(f"Run criada em: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
