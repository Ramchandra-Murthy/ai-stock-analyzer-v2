"""Compare backtest outcomes across explicitly supplied parameter variants.

This research helper does not fetch data, optimize parameters, or execute trades.
Callers supply each named BacktestConfig so the tested assumptions remain auditable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

from modules.fibonacci_gann.backtest import BacktestConfig, BacktestResult, Candle, run_backtest


@dataclass(frozen=True)
class ParameterSensitivityResult:
    """Backtest outcome for one named parameter configuration."""

    variant: str
    config: BacktestConfig
    result: BacktestResult


def evaluate_parameter_sensitivity(
    candles: Sequence[Candle],
    signals: Sequence[bool],
    variants: Mapping[str, BacktestConfig],
) -> tuple[ParameterSensitivityResult, ...]:
    """Run the same candles/signals independently under named configurations.

    Variants are evaluated in mapping order. Each run starts with the capital
    specified by its own config; returns are not compounded across variants.
    """
    if len(candles) != len(signals):
        raise ValueError("signals length must equal candles length")
    if not variants:
        raise ValueError("at least one parameter variant is required")
    if any(not isinstance(signal, bool) for signal in signals):
        raise ValueError("signals must contain only booleans")

    results: list[ParameterSensitivityResult] = []
    for name, config in variants.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("variant names must be non-empty strings")
        if not isinstance(config, BacktestConfig):
            raise ValueError(f"variant {name!r} must use a BacktestConfig")
        result = run_backtest(candles, signals, config)
        metrics = (
            result.total_return_pct,
            result.win_rate_pct,
            result.expectancy_per_trade,
            result.profit_factor,
            result.max_drawdown_pct,
        )
        if not all(isfinite(value) for value in metrics):
            raise ValueError(f"variant {name!r} produced non-finite performance metrics")
        results.append(ParameterSensitivityResult(name, config, result))
    return tuple(results)


@dataclass(frozen=True)
class ParameterGridCase:
    """One lookback/reward-risk pair for a transparent research grid."""

    lookback: int
    reward_risk_ratio: float
    config: BacktestConfig


def build_parameter_grid(
    base_config: BacktestConfig,
    lookbacks: Sequence[int] = (10, 20, 30, 50),
    reward_risk_ratios: Sequence[float] = (2.0, 2.5, 3.0),
) -> tuple[ParameterGridCase, ...]:
    """Build a deterministic lookback x reward/risk grid without ranking outcomes.

    The caller must regenerate causal signals independently for each lookback.
    This helper only creates configurations; it does not choose a winner.
    """
    if not isinstance(base_config, BacktestConfig):
        raise ValueError("base_config must be a BacktestConfig")
    if not lookbacks or not reward_risk_ratios:
        raise ValueError("lookbacks and reward/risk ratios must not be empty")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in lookbacks
    ):
        raise ValueError("lookbacks must be positive integers")
    if any(not isfinite(value) or value <= 0 for value in reward_risk_ratios):
        raise ValueError("reward/risk ratios must be finite and greater than zero")
    if len(set(lookbacks)) != len(lookbacks):
        raise ValueError("lookbacks must not contain duplicates")
    if len(set(reward_risk_ratios)) != len(reward_risk_ratios):
        raise ValueError("reward/risk ratios must not contain duplicates")

    return tuple(
        ParameterGridCase(
            lookback=lookback,
            reward_risk_ratio=ratio,
            config=BacktestConfig(
                capital=base_config.capital,
                max_loss_per_trade=base_config.max_loss_per_trade,
                stop_distance=base_config.stop_distance,
                reward_risk_ratio=ratio,
                round_trip_cost_per_unit=base_config.round_trip_cost_per_unit,
                slippage_per_unit_per_side=base_config.slippage_per_unit_per_side,
            ),
        )
        for lookback in lookbacks
        for ratio in reward_risk_ratios
    )
