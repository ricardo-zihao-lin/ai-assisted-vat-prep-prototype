from __future__ import annotations

import pandas as pd


def read_output_csv(file_path: str | None, default_columns: list[str] | None = None) -> pd.DataFrame:
    if not file_path:
        return pd.DataFrame(columns=default_columns or [])
    try:
        return pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=default_columns or [])

