from pathlib import Path

import pandas as pd
import pytest

from engine.nifty_options_v2_ingestion import load_verified_options_csv


def test_load_verified_options_csv_normalizes_valid_data(tmp_path: Path) -> None:
    path = tmp_path / "options.csv"
    pd.DataFrame(
        {
            "observed_date": ["2021-05-27"],
            "expiry": ["2021-06-24"],
            "strike": [15000],
            "spot": [15300],
            "ltp": [420],
        }
    ).to_csv(path, index=False)

    result = load_verified_options_csv(path)

    assert result.loc[0, "observed_date"].isoformat() == "2021-05-27"
    assert result.loc[0, "expiry"].isoformat() == "2021-06-24"
    assert result.loc[0, "strike"] == 15000
    assert result.loc[0, "ltp"] == 420


def test_load_verified_options_csv_rejects_invalid_values(tmp_path: Path) -> None:
    path = tmp_path / "options.csv"
    pd.DataFrame(
        {
            "observed_date": ["2021-05-27"],
            "expiry": ["2021-06-24"],
            "strike": [15000],
            "spot": [15300],
            "ltp": [-1],
        }
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="ltp must be non-negative"):
        load_verified_options_csv(path)
