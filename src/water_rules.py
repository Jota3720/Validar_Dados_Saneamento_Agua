from __future__ import annotations

import pandas as pd


def validate_water_topology(nodes: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    # In the local working project this is resolved with the current GIA.A mapping.
    # This published snapshot keeps the public contract explicit.
    return pd.DataFrame(columns=["regra_id", "source_layer", "source_id", "tipo_erro", "gravidade"])
