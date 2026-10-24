"""Historical-data interfaces for NIFTY Options Book V2."""

from __future__ import annotations

from datetime import date

from strategy.nifty_options_v2 import NiftyCallObservation


class HistoricalOptionsData:
    """Provide validated observations to the V2 backtest without inventing data."""

    def get_observation(
        self,
        *,
        expiry: date,
        strike: float,
        observed_date: date,
    ) -> NiftyCallObservation:
        """Return one historical observation.

        Concrete data providers must implement this method. The V2 baseline
        deliberately does not fabricate market prices when historical data is
        unavailable.
        """
        raise NotImplementedError("A historical options data provider is required")
