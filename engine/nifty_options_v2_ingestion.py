"""Ingestion boundary for verified NIFTY Options Book V2 CSV data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from engine.nifty_options_v2_data_validation import validate_options_frame


def load_verified_options_csv(path: str | Path) -> pd.DataFrame:
    """Load and validate a historical NIFTY options observation CSV.

    This function intentionally performs no web download or price inference.
    The caller is responsible for supplying a verified historical dataset.
    """
    frame = pd.read_csv(Path(path))
    return validate_options_frame(frame)
