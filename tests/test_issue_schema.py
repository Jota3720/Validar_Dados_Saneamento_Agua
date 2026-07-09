from __future__ import annotations

import pandas as pd

from src.issue_schema import ISSUE_COLUMNS, normalize_issues


def test_normalize_issues_converts_legacy_columns():
    df = pd.DataFrame(
        [
            {
                "regra_id": "SAN_ATT_001",
                "tipo_erro": "ID nulo",
                "gravidade": "ALTA",
                "source_layer": "x",
                "source_id": None,
            }
        ]
    )
    result = normalize_issues(df, domain="SANEAMENTO", run_id="run_1")
    assert list(result.columns) == ISSUE_COLUMNS
    assert result.iloc[0]["message"] == "ID nulo"
    assert result.iloc[0]["severity"] == "ALTA"
    assert result.iloc[0]["domain"] == "SANEAMENTO"
    assert result.iloc[0]["run_id"] == "run_1"
