from __future__ import annotations

import csv
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

GEOMETRY_COLUMNS = {
    "geometry",
    "geometry_wkt",
    "geometria_wkt",
    "wkt",
    "geom_wkt",
}

PREFERRED_COLUMNS = [
    "run_id",
    "domain",
    "gravidade",
    "severity",
    "tema",
    "theme",
    "regra",
    "regra_id",
    "camada",
    "source_layer",
    "id_entidade",
    "source_id",
    "grupo_modelo",
    "model_group",
    "tipo_entidade",
    "entity_type",
    "erro",
    "message",
    "correcao_sugerida",
    "suggested_fix",
]


def _run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "ERRO: git não está disponível no PATH"

    text = (result.stdout or result.stderr).strip()
    return text or f"Comando terminou com código {result.returncode} sem output."


def _detect_domain(path: Path, df: pd.DataFrame) -> str | None:
    if "domain" in df.columns and not df.empty:
        values = df["domain"].dropna().astype(str).str.upper().unique().tolist()
        if "AGUA" in values or "ÁGUA" in values:
            return "agua"
        if "SANEAMENTO" in values:
            return "saneamento"

    marker = str(path).lower()
    if "agua" in marker or "water" in marker or "_wat" in marker:
        return "agua"
    if "saneamento" in marker or "sewer" in marker or "_san" in marker:
        return "saneamento"
    return None


def _candidate_error_files() -> list[Path]:
    if not OUTPUTS.exists():
        return []

    names = {
        "validacao_erros_legivel.csv",
        "validacao_erros.csv",
        "amostra_casos_reais.csv",
    }
    return [p for p in OUTPUTS.rglob("*.csv") if p.name.lower() in names]


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except Exception as exc:  # pragma: no cover - depends on local files
            last_error = exc
    raise RuntimeError(f"Não foi possível ler {path}: {last_error}")


def _latest_sources() -> dict[str, tuple[Path, pd.DataFrame]]:
    selected: dict[str, tuple[Path, pd.DataFrame]] = {}

    for path in sorted(_candidate_error_files(), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            df = _read_csv(path)
        except Exception:
            continue
        domain = _detect_domain(path, df)
        if domain and domain not in selected:
            selected[domain] = (path, df)
        if len(selected) == 2:
            break

    return selected


def _safe_sample(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    safe = df.copy()
    drop_cols = [c for c in safe.columns if str(c).strip().lower() in GEOMETRY_COLUMNS]
    if drop_cols:
        safe = safe.drop(columns=drop_cols)

    ordered = [c for c in PREFERRED_COLUMNS if c in safe.columns]
    remaining = [c for c in safe.columns if c not in ordered]
    safe = safe[ordered + remaining]
    return safe.head(limit)


def _write_git_state(path: Path) -> None:
    sections = {
        "PASTA": str(ROOT),
        "GIT_ROOT": _run_git("rev-parse", "--show-toplevel"),
        "BRANCH": _run_git("branch", "--show-current"),
        "STATUS": _run_git("status", "--short", "--branch"),
        "REMOTES": _run_git("remote", "-v"),
        "ULTIMOS_COMMITS": _run_git("log", "-10", "--oneline", "--decorate"),
    }
    content = []
    for title, value in sections.items():
        content.append(f"===== {title} =====\n{value}\n")
    path.write_text("\n".join(content), encoding="utf-8")


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_dir = OUTPUTS / "auditoria" / timestamp
    audit_dir.mkdir(parents=True, exist_ok=True)

    _write_git_state(audit_dir / "estado_git_local.txt")
    sources = _latest_sources()
    manifest_rows: list[dict[str, object]] = []

    for domain in ("agua", "saneamento"):
        source = sources.get(domain)
        if source is None:
            manifest_rows.append(
                {
                    "domain": domain,
                    "status": "nao_encontrado",
                    "source_file": "",
                    "source_records": 0,
                    "sample_file": "",
                    "sample_records": 0,
                    "note": "Não foi encontrado CSV de erros local para este domínio.",
                }
            )
            continue

        source_path, df = source
        sample = _safe_sample(df, limit=20)
        sample_path = audit_dir / f"{domain}_casos_reais_20.csv"
        sample.to_csv(sample_path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

        manifest_rows.append(
            {
                "domain": domain,
                "status": "ok",
                "source_file": str(source_path),
                "source_records": len(df),
                "sample_file": str(sample_path),
                "sample_records": len(sample),
                "note": "Amostra sem colunas de geometria.",
            }
        )

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(audit_dir / "manifest_auditoria.csv", index=False, encoding="utf-8-sig")

    readme = [
        "PACOTE DE AUDITORIA LOCAL",
        "",
        f"Pasta do projecto analisada: {ROOT}",
        f"Pasta do pacote: {audit_dir}",
        "",
        "Este script não alterou código, não ligou à Oracle e não apagou ficheiros.",
        "",
        "Ficheiros principais:",
        "- estado_git_local.txt",
        "- manifest_auditoria.csv",
        "- agua_casos_reais_20.csv, se encontrado",
        "- saneamento_casos_reais_20.csv, se encontrado",
    ]
    (audit_dir / "LEIA-ME.txt").write_text("\n".join(readme), encoding="utf-8")

    print(f"Auditoria criada em: {audit_dir}")
    print(manifest.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
