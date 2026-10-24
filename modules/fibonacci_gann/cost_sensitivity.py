"""Transaction-cost and slippage sensitivity analysis for research backtests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from math import isfinite

from modules.fibonacci_gann.backtest import (
    BacktestConfig,
    BacktestResult,
    Candle,
    run_backtest,
)


@dataclass(frozen=True)
class CostSensitivityRow:
    """Backtest metrics for one explicitly configured cost assumption."""

    round_trip_cost_per_unit: float
    slippage_per_unit_per_side: float
    result: BacktestResult


def evaluate_cost_sensitivity(
    candles: Sequence[Candle],
    signals: Sequence[bool],
    base_config: BacktestConfig,
    *,
    round_trip_costs: Sequence[float],
    slippage_per_side_values: Sequence[float],
) -> tuple[CostSensitivityRow, ...]:
    """Rerun fixed signals across cost/slippage combinations.

    Signals are held constant so this isolates execution-cost assumptions; it
    does not model how costs could change the signal-generation process.
    """
    if not round_trip_costs:
        raise ValueError("round_trip_costs must not be empty")
    if not slippage_per_side_values:
        raise ValueError("slippage_per_side_values must not be empty")
    for name, values in (
        ("round_trip_costs", round_trip_costs),
        ("slippage_per_side_values", slippage_per_side_values),
    ):
        for value in values:
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} values must be finite and non-negative")

    rows: list[CostSensitivityRow] = []
    for cost in round_trip_costs:
        for slippage in slippage_per_side_values:
            config = replace(
                base_config,
                round_trip_cost_per_unit=float(cost),
                slippage_per_unit_per_side=float(slippage),
            )
            result = run_backtest(candles, signals, config)
            rows.append(
                CostSensitivityRow(
                    round_trip_cost_per_unit=float(cost),
                    slippage_per_unit_per_side=float(slippage),
                    result=result,
                )
            )
    return tuple(rows)
