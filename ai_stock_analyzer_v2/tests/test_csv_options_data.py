from datetime import date

import pandas as pd
import pytest

from engine.csv_options_data import CsvHistoricalOptionsData


def test_csv_provider_returns_exact_observation(tmp_path) -> None:
    path = tmp_path / "options.csv"
    pd.DataFrame(
        [
            {
                "observed_date": "2021-05-27",
                "expiry": "2021-06-24",
                "strike": 15000,
                "spot": 15300,
                "ltp": 420,
            }
        ]
    ).to_csv(path, index=False)

    provider = CsvHistoricalOptionsData(path)
    observation = provider.get_observation(
        expiry=date(2021, 6, 24), strike=15000, observed_date=date(2021, 5, 27)
    )

    assert observation.spot == 15300
    assert observation.ltp == 420
    assert observation.is_itm


def test_csv_provider_rejects_missing_columns(tmp_path) -> None:
    path = tmp_path / "options.csv"
    pd.DataFrame([{"expiry": "2021-06-24"}]).to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        CsvHistoricalOptionsData(path)


def test_csv_provider_rejects_missing_observation(tmp_path) -> None:
    path = tmp_path / "options.csv"
    pd.DataFrame(
        [
            {
                "observed_date": "2021-05-27",
                "expiry": "2021-06-24",
                "strike": 15000,
                "spot": 15300,
                "ltp": 420,
            }
        ]
    ).to_csv(path, index=False)

    provider = CsvHistoricalOptionsData(path)
    with pytest.raises(KeyError, match="No historical observation"):
        provider.get_observation(
            expiry=date(2021, 6, 24), strike=15100, observed_date=date(2021, 5, 27)
        )
