from __future__ import annotations
import os
import glob
import pandas as pd # type: ignore

def load_first_csv(data_dir: str = "data") -> pd.DataFrame | None:
    os.makedirs(data_dir, exist_ok=True)
    csvs = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not csvs:
        return None
    # Adjust parse_dates to match your eventual schema if needed
    try:
        return pd.read_csv(csvs[0], low_memory=False)
    except Exception:
        # Last resort: read without type hints
        return pd.read_csv(csvs[0])
