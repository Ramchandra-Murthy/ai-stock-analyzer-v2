"""Multi-year orchestration for the NIFTY Options Book V2 backtest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.nifty_options_v2_backtest import NiftyOptionsV2Backtest
from engine.nifty_options_v2_monthly import MonthlyV2Runner, MonthlyV2Trade


@dataclass(frozen=True)
class V2SeriesSpec:
    """Explicit specification for one historical monthly series."""

    series: str
    expiry: date
    strike: float
    entry_date: date
    exit_date: date


class MultiYearV2Runner:
    """Run explicit monthly specifications across any requested date range."""

    def __init__(self, backtest: NiftyOptionsV2Backtest) -> None:
        self.monthly = MonthlyV2Runner(backtest)

    def run(self, specifications: list[V2SeriesSpec]) -> list[MonthlyV2Trade]:
        """Run only the historical series explicitly supplied by the caller."""
        tuples = [
            (item.series, item.expiry, item.strike, item.entry_date, item.exit_date)
            for item in specifications
        ]
        return self.monthly.run(tuples)

    @staticmethod
    def total_points(results: list[MonthlyV2Trade]) -> float:
        """Return cumulative points across all supplied series."""
        return MonthlyV2Runner.total_points(results)
