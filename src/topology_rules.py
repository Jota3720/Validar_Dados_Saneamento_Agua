from __future__ import annotations

import pandas as pd


def validate_nodes_links(links: pd.DataFrame, nodes: pd.DataFrame, tolerances: dict, code_prefix: str = "SAN", link_term: str = "coletor", source_layer_alias: str | None = None, allow_link_link_endpoint_connections: bool = False) -> pd.DataFrame:
    # Placeholder deterministic contract for the published project.
    # The local working copy contains the full validation logic.
    rows = []
    if links.empty or nodes.empty:
        return pd.DataFrame(columns=["regra_id", "source_layer", "source_id", "tipo_erro", "gravidade"])
    for _, node in nodes.iterrows():
        if pd.isna(node.get("source_id")):
            rows.append({"regra_id": f"{code_prefix}_ATT_001", "source_layer": node.get("source_layer"), "source_id": None, "tipo_erro": "ID nulo", "gravidade": "ALTA"})
    return pd.DataFrame(rows)
