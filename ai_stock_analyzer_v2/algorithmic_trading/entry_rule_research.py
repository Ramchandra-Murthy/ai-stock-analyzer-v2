"""Compare candidate entry rules under shared backtest assumptions.

This module evaluates precomputed signals; it does not generate, tune, or
select strategies. Signals must be causal and must use comparable timestamps.
"""

from __future__ import annotations

import pandas as pd

from algorithmic_trading.backtester import compare_timeframe_backtests
from algorithmic_trading.trading_costs import IndiaEquityCostModel


def compare_entry_rules(
    strategy_data: dict[str, tuple[pd.Series, pd.Series]],
    initial_capital: float = 100_000.0,
    cost_bps: float = 10.0,
    cost_model: IndiaEquityCostModel | None = None,
) -> pd.DataFrame:
    """Compare precomputed entry-rule price/signal pairs.

    Mapping values contain a price series and a target-position signal series
    for one named entry rule. Every candidate uses the same initial capital
    and transaction-cost assumptions. Results are descriptive comparisons,
    not an automatic recommendation of the highest-scoring strategy.
    """
    if not strategy_data:
        raise ValueError("strategy_data must contain at least one entry rule")

    for name in strategy_data:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("entry-rule names must be non-empty strings")

    comparison = compare_timeframe_backtests(
        strategy_data,
        initial_capital=initial_capital,
        cost_bps=cost_bps,
        cost_model=cost_model,
    )
    comparison.index = pd.Index(comparison.index, name="entry_rule")
    return comparison
