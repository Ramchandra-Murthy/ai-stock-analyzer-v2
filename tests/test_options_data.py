"""Tests for the V2 historical-data interface."""

from datetime import date

import pytest

from engine.options_data import HistoricalOptionsData


def test_historical_data_provider_requires_implementation() -> None:
    provider = HistoricalOptionsData()

    with pytest.raises(NotImplementedError, match="historical options data provider"):
        provider.get_observation(
            expiry=date(2026, 10, 29),
            strike=25000,
            observed_date=date(2026, 10, 1),
        )
