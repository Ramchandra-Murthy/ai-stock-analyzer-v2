"""Dynamic asset-allocation controls for NSE/BSE research.

The implementation follows the allocation and dynamic-risk concepts described
in Chapter 9 of Laurent Bernut's *Algorithmic Short Selling with Python,
Second Edition*, adapted for the project's NSE/BSE research pipeline.

It deliberately exposes the risk appetite as an auditable time series rather
than hiding regime-dependent exposure changes inside a black-box optimizer.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from algorithmic_trading.asset_allocation import (
    apply_weight_cap,
    equal_weight,
    inverse_volatility_weight,
    minimum_variance_weight,
)
from algorithmic_trading.portfolio_risk import dynamic_risk_appetite


@dataclass(frozen=True)
class DynamicAllocationConfig:
    """Configuration for drawdown-aware dynamic exposure allocation."""

    method: str = "equal"
    max_weight: float = 0.20
    max_drawdown_tolerance: float = -0.10
    min_risk: float = 0.25
    max_risk: float = 1.00
    smoothing_span: int = 20
    curve_shape: str = "linear"


def base_allocation(
    returns: pd.DataFrame,
    method: str,
) -> pd.Series:
    """Build a transparent long-only allocation baseline."""
    if method == "equal":
        return equal_weight(returns)
    if method == "inverse_volatility":
        return inverse_volatility_weight(returns)
    if method == "minimum_variance":
        return minimum_variance_weight(returns)
    raise ValueError("unsupported allocation method")


def dynamic_asset_allocation(
    returns: pd.DataFrame,
    equity_curve: pd.Series,
    config: DynamicAllocationConfig | None = None,
) -> pd.DataFrame:
    """Return time-varying weights scaled by drawdown-based risk appetite.

    The base allocation determines relative weights between assets. The
    dynamic risk appetite determines the portfolio's total gross exposure.
    Therefore a drawdown can reduce exposure without changing the relative
    ranking of the selected assets.
    """
    settings = config or DynamicAllocationConfig()
    if returns.empty:
        return pd.DataFrame(index=equity_curve.index, columns=returns.columns)
    if equity_curve.empty:
        raise ValueError("equity_curve must not be empty")
    if settings.max_weight <= 0 or settings.max_weight > 1:
        raise ValueError("max_weight must be between 0 and 1")

    aligned_returns = returns.copy()
    equity = pd.Series(equity_curve, dtype=float).dropna()
    if equity.empty:
        raise ValueError("equity_curve must contain numeric values")

    base = base_allocation(aligned_returns, settings.method)
    base = apply_weight_cap(base, settings.max_weight)

    appetite = dynamic_risk_appetite(
        equity,
        max_drawdown_tolerance=settings.max_drawdown_tolerance,
        min_risk=settings.min_risk,
        max_risk=settings.max_risk,
        smoothing_span=settings.smoothing_span,
        curve_shape=settings.curve_shape,
    )

    weights = pd.DataFrame(
        0.0,
        index=appetite.index,
        columns=base.index,
    )
    for timestamp, risk in appetite.items():
        weights.loc[timestamp] = base * float(risk)

    return weights


def latest_dynamic_allocation(
    returns: pd.DataFrame,
    equity_curve: pd.Series,
    config: DynamicAllocationConfig | None = None,
) -> pd.Series:
    """Return the latest drawdown-adjusted target weights."""
    allocation = dynamic_asset_allocation(returns, equity_curve, config)
    if allocation.empty:
        return pd.Series(dtype=float)
    return allocation.iloc[-1].copy()
