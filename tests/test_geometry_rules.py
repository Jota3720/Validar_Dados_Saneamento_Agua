from __future__ import annotations

import pandas as pd

from src.geometry_rules import validate_geometry


class DummyGeom:
    is_empty = False
    is_valid = True
    length = 1.0


def test_validate_geometry_returns_empty_frame_for_valid_data():
    df = pd.DataFrame([{"geometry": DummyGeom(), "source_layer": "x", "source_id": 1}])
    result = validate_geometry(df)
    assert result.empty
