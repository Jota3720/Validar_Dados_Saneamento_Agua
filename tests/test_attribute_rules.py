from __future__ import annotations

import pandas as pd

from src.attribute_rules import validate_required_attributes


def test_validate_required_attributes_detects_missing_id_and_diameter():
    df = pd.DataFrame([{"source_layer": "x", "source_id": None, "diameter_mm": None}])
    result = validate_required_attributes(df, "LINK")
    assert len(result) >= 2
