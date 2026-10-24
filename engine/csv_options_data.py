"""CSV-backed historical data provider for NIFTY Options Book V2."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from strategy.nifty_options_v2 import NiftyCallContract, NiftyCallObservation


class CsvHistoricalOptionsData:
    """Load verified NIFTY CALL observations from a user-supplied CSV file."""

    REQUIRED_COLUMNS = frozenset({"observed_date", "expiry", "strike", "spot", "ltp"})

    def __init__(self, csv_path: str | Path) -> None:
        self.csv_path = Path(csv_path)
        frame = pd.read_csv(self.csv_path)
        missing = self.REQUIRED_COLUMNS.difference(frame.columns)
        if missing:
            missing_columns = ", ".join(sorted(missing))
            raise ValueError(f"CSV is missing required columns: {missing_columns}")
        self._frame = frame.copy()
        self._frame["observed_date"] = pd.to_datetime(
            self._frame["observed_date"], errors="raise"
        ).dt.date
        self._frame["expiry"] = pd.to_datetime(self._frame["expiry"], errors="raise").dt.date

    def get_observation(
        self, *, expiry: date, strike: float, observed_date: date
    ) -> NiftyCallObservation:
        """Return the exact historical observation requested."""
        matches = self._frame.loc[
            (self._frame["expiry"] == expiry)
            & (self._frame["strike"] == strike)
            & (self._frame["observed_date"] == observed_date)
        ]
        if matches.empty:
            raise KeyError("No historical observation for the requested contract and date")
        if len(matches) > 1:
            raise ValueError("Multiple historical observations match the request")
        row = matches.iloc[0]
        return NiftyCallObservation(
            contract=NiftyCallContract(expiry=expiry, strike=float(row["strike"])),
            observed_date=observed_date,
            spot=float(row["spot"]),
            ltp=float(row["ltp"]),
        )
