from __future__ import annotations

import pandas as pd

from src.topology_rules import validate_nodes_links


def test_validate_nodes_links_returns_frame():
    links = pd.DataFrame([{"source_layer": "a", "source_id": 1}])
    nodes = pd.DataFrame([{"source_layer": "b", "source_id": None}])
    result = validate_nodes_links(links, nodes, {})
    assert not result.empty
