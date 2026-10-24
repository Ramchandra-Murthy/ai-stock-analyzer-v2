"""Portfolio exposure and dynamic risk controls for NSE/BSE research."""

from __future__ import annotations

import numpy as np
import pandas as pd


def market_value(position: pd.Series, price: pd.Series) -> pd.Series:
    """Calculate position market values."""
    return position * price


def net_asset_value(market_values: pd.DataFrame, cash: pd.Series) -> pd.Series:
    """Calculate portfolio NAV from cash and position market values."""
    return cash + market_values.sum(axis=1)


def gross_exposure(market_values: pd.DataFrame, nav: pd.Series) -> pd.Series:
    """Calculate absolute portfolio exposure as a fraction of NAV."""
    return market_values.abs().sum(axis=1).div(nav)


def net_exposure(market_values: pd.DataFrame, nav: pd.Series) -> pd.Series:
    """Calculate signed portfolio exposure as a fraction of NAV."""
    return market_values.sum(axis=1).div(nav)


def net_beta_exposure(
    market_values: pd.DataFrame,
    beta: pd.Series,
    nav: pd.Series,
) -> pd.Series:
    """Calculate beta-weighted signed exposure as a fraction of NAV."""
    beta_weighted = market_values.mul(beta, axis=1)
    return beta_weighted.sum(axis=1).div(nav)


def dynamic_risk_appetite(
    equity_curve: pd.Series,
    max_drawdown_tolerance: float,
    min_risk: float,
    max_risk: float,
    smoothing_span: int = 20,
    curve_shape: str = "linear",
    drawdown_window: int = 0,
) -> pd.Series:
    """Scale risk appetite between bounds as drawdown changes.

    This follows the Chapter 8 risk-appetite framework: calculate drawdown
    from a peak, normalize it to the maximum tolerated drawdown, smooth the
    result, apply a response curve, then map it to the risk range.
    """
    if max_drawdown_tolerance >= 0:
        raise ValueError("max_drawdown_tolerance must be negative")
    if min_risk < 0 or max_risk < min_risk:
        raise ValueError("risk bounds are invalid")
    if smoothing_span <= 0 or drawdown_window < 0:
        raise ValueError("window parameters are invalid")
    if curve_shape not in {"linear", "aggressive", "conservative"}:
        raise ValueError("unsupported curve_shape")

    equity = pd.Series(equity_curve, dtype=float)
    if drawdown_window > 0:
        running_max = equity.rolling(
            window=drawdown_window,
            min_periods=1,
        ).max()
    else:
        running_max = equity.expanding().max()

    drawdown = equity.div(running_max).sub(1.0)
    normalized = 1.0 - np.minimum(
        drawdown.div(max_drawdown_tolerance),
        1.0,
    )
    smoothed = normalized.ewm(span=smoothing_span).mean()

    if curve_shape == "aggressive":
        power = min_risk / max_risk if max_risk > 0 else 1.0
    elif curve_shape == "conservative":
        power = max_risk / min_risk if min_risk > 0 else 1.0
    else:
        power = 1.0

    transformed = smoothed.pow(power)
    return min_risk + (max_risk - min_risk) * transformed
