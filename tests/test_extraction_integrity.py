from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from src.normalization import normalize_links
from src.oracle_extract import diagnose_wkt_text


def test_diagnose_wkt_text_classifies_null_and_ok():
    null_case = diagnose_wkt_text(None)
    ok_case = diagnose_wkt_text("POINT (1 2)")

    assert null_case["diagnostic_reason"] == "NULL_GEOMETRY"
    assert null_case["geometry_parse_ok"] is False
    assert ok_case["diagnostic_reason"] == "OK"
    assert ok_case["geometry_parse_ok"] is True
    assert ok_case["geometry_type"] == "Point"


def test_diagnose_wkt_text_flags_large_invalid_wkt_as_truncated():
    large_invalid = "POINT (" + ("1 2," * 9000) + "1 2)"
    result = diagnose_wkt_text(large_invalid)

    assert len(large_invalid) > 32767
    assert result["diagnostic_reason"] == "WKT_TRUNCATED"
    assert result["geometry_parse_ok"] is False
    assert result["parse_error"]


def test_normalize_links_preserves_integrity_columns():
    gdf = gpd.GeoDataFrame(
        pd.DataFrame(
            [
                {
                    "IPID": 1,
                    "DIAMETRO": 200,
                    "diagnostic_reason": "OK",
                    "source_wkt_length": 12,
                    "extracted_wkt_length": 12,
                }
            ]
        ),
        geometry=[Point(0, 0)],
        crs=3763,
    )

    result = normalize_links(
        {"tubagens": gdf},
        {
            "tubagens": {
                "id_field": "IPID",
                "diameter_field": "DIAMETRO",
                "entity_type": "tubagem",
            }
        },
    )

    assert "diagnostic_reason" in result.columns
    assert "source_wkt_length" in result.columns
    assert "extracted_wkt_length" in result.columns
    assert result.loc[0, "diagnostic_reason"] == "OK"
