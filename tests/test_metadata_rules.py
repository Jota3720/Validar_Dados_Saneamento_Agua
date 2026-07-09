from __future__ import annotations

import pandas as pd

from src.metadata_rules import validate_location_metadata


def test_validate_location_metadata_flags_missing_fields():
    df = pd.DataFrame([{"source_layer": "ramal", "source_id": 1, "model_group": "RAMAL", "arruamento": None, "freguesia_caop_2012": None, "freguesia_caop_2017": None, "numero_policia": None}])
    result = validate_location_metadata(df)
    assert len(result) >= 4
