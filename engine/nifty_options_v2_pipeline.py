"""End-to-end pipeline for the NIFTY Options Book V2 backtest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.nifty_options_v2_backtest import NiftyOptionsV2Backtest
from engine.nifty_options_v2_monthly import MonthlyV2Runner, MonthlyV2Trade
from engine.nifty_options_v2_report import V2BacktestReport, build_report
from strategy.nifty_options_v2_strikes import select_deepest_itm_call


@dataclass(frozen=True)
class V2SeriesInput:
    """Explicit market observations and available strikes for one series."""

    series: str
    expiry: date
    entry_date: date
    exit_date: date
    spot_entry: float
    available_strikes: list[float]


class NiftyOptionsV2Pipeline:
    """Connect strike selection, monthly execution, and reporting."""

    def __init__(self, backtest: NiftyOptionsV2Backtest) -> None:
        self.backtest = backtest

    def run(
        self, series_inputs: list[V2SeriesInput]
    ) -> tuple[list[MonthlyV2Trade], V2BacktestReport]:
        """Run explicit series inputs and return trades plus aggregate report."""
        specifications = []
        for item in series_inputs:
            strike = select_deepest_itm_call(item.available_strikes, item.spot_entry)
            specifications.append(
                (item.series, item.expiry, strike, item.entry_date, item.exit_date)
            )
        trades = MonthlyV2Runner(self.backtest).run(specifications)
        return trades, build_report(trades)
