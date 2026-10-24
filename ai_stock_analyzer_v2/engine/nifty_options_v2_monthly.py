"""Monthly-series runner for the frozen NIFTY Options Book V2 rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.nifty_options_v2_backtest import NiftyOptionsV2Backtest, V2BacktestTrade


@dataclass(frozen=True)
class MonthlyV2Trade:
    """One monthly V2 trade with its series label."""

    series: str
    trade: V2BacktestTrade

    @property
    def points_pnl(self) -> float:
        return self.trade.points_pnl


class MonthlyV2Runner:
    """Run a supplied sequence of monthly V2 trade specifications."""

    def __init__(self, backtest: NiftyOptionsV2Backtest) -> None:
        self.backtest = backtest

    def run(
        self,
        specifications: list[tuple[str, date, float, date, date]],
    ) -> list[MonthlyV2Trade]:
        """Run monthly specifications without inventing dates or strikes."""
        results: list[MonthlyV2Trade] = []
        for series, expiry, strike, entry_date, exit_date in specifications:
            results.append(
                MonthlyV2Trade(
                    series=series,
                    trade=self.backtest.run_trade(
                        expiry=expiry,
                        strike=strike,
                        entry_date=entry_date,
                        exit_date=exit_date,
                    ),
                )
            )
        return results

    @staticmethod
    def total_points(results: list[MonthlyV2Trade]) -> float:
        """Return cumulative points P&L across monthly trades."""
        return sum(result.points_pnl for result in results)
