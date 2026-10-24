"""Chapter 8 long/short portfolio toolbox.

Implements the core portfolio-level exposure and risk controls described in
Chapter 8: gross exposure, dynamic risk appetite, net exposure, net beta,
concentration, big/small bet disparity, exchange exposure, and sector
exposure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def market_value(position: pd.DataFrame | pd.Series, price: pd.DataFrame | pd.Series):
    """Calculate signed market value from position size and current price."""
    return position * price


def net_asset_value(market_values: pd.DataFrame, cash: pd.Series | float) -> pd.Series:
    """Calculate NAV as cash plus the sum of signed position market values."""
    return pd.Series(cash, index=market_values.index) + market_values.sum(axis=1)


def gross_exposure(market_values: pd.DataFrame, nav: pd.Series | float) -> pd.Series:
    """Calculate gross exposure as absolute market value divided by NAV."""
    return _divide_by_nav(market_values.abs().sum(axis=1), nav)


def net_exposure(market_values: pd.DataFrame, nav: pd.Series | float) -> pd.Series:
    """Calculate signed net exposure divided by NAV."""
    return _divide_by_nav(market_values.sum(axis=1), nav)


def net_beta_exposure(
    market_values: pd.DataFrame,
    beta: pd.Series | pd.DataFrame,
    nav: pd.Series | float,
) -> pd.Series:
    """Calculate beta-weighted net exposure divided by NAV."""
    beta_weighted = market_values.mul(beta, axis="columns")
    return _divide_by_nav(beta_weighted.sum(axis=1), nav)


def risk_appetite(
    equity_curve: pd.Series | np.ndarray | list[float],
    max_drawdown_tolerance: float,
    min_risk: float,
    max_risk: float,
    smoothing_span: int = 20,
    curve_shape: str = "linear",
    drawdown_window: int = 0,
) -> pd.Series:
    """Scale target risk between min and max according to drawdown.

    max_drawdown_tolerance follows Chapter 8 and is expressed as a negative
    drawdown, for example -0.05 for -5%.
    """
    if max_drawdown_tolerance >= 0:
        raise ValueError("max_drawdown_tolerance must be negative")
    if min_risk < 0 or max_risk <= 0 or min_risk > max_risk:
        raise ValueError("risk bounds must satisfy 0 <= min_risk <= max_risk")
    if smoothing_span < 1:
        raise ValueError("smoothing_span must be at least 1")
    if drawdown_window < 0:
        raise ValueError("drawdown_window must be non-negative")
    if curve_shape not in {"linear", "aggressive", "conservative"}:
        raise ValueError("curve_shape must be linear, aggressive, or conservative")

    equity = pd.Series(equity_curve, dtype=float)
    if equity.empty:
        return pd.Series(dtype=float, index=equity.index, name="risk_appetite")

    if drawdown_window > 0:
        running_max = equity.rolling(drawdown_window, min_periods=1).max()
    else:
        running_max = equity.expanding().max()

    drawdown = equity / running_max - 1
    normalized = 1 - np.minimum(drawdown / max_drawdown_tolerance, 1)
    smoothed = normalized.ewm(span=smoothing_span).mean()

    power_map = {
        "aggressive": min_risk / max_risk if max_risk else 1.0,
        "conservative": max_risk / min_risk if min_risk else 1.0,
        "linear": 1.0,
    }
    power = power_map[curve_shape]
    transformed = smoothed**power
    result = min_risk + (max_risk - min_risk) * transformed
    return result.clip(lower=min_risk, upper=max_risk).rename("risk_appetite")


def concentration(market_values: pd.DataFrame) -> pd.Series:
    """Count non-zero positions in each portfolio observation."""
    return market_values.ne(0).sum(axis=1).rename("concentration")


def long_short_counts(market_values: pd.DataFrame) -> pd.DataFrame:
    """Return the number of long and short positions per observation."""
    return pd.DataFrame(
        {
            "long_count": market_values.gt(0).sum(axis=1),
            "short_count": market_values.lt(0).sum(axis=1),
        }
    )


def big_small_bet_ratio(market_values: pd.DataFrame) -> pd.Series:
    """Return largest-to-smallest non-zero absolute position value ratio."""
    absolute_values = market_values.abs().where(market_values.ne(0))
    largest = absolute_values.max(axis=1)
    smallest = absolute_values.min(axis=1)
    result = largest.div(smallest).where(smallest.notna() & smallest.ne(0))
    return result.rename("big_small_bet_ratio")


def grouped_exposure(
    market_values: pd.DataFrame,
    groups: pd.Series,
    nav: pd.Series | float,
) -> pd.DataFrame:
    """Calculate signed exposure by exchange or sector group."""
    group_map = pd.Series(groups)
    valid_columns = [column for column in market_values.columns if column in group_map.index]
    if not valid_columns:
        return pd.DataFrame(index=market_values.index)

    grouped = market_values[valid_columns].T.groupby(group_map.loc[valid_columns]).sum().T
    return grouped.div(pd.Series(nav, index=market_values.index), axis=0)


def exchange_exposure(
    market_values: pd.DataFrame,
    exchanges: pd.Series,
    nav: pd.Series | float,
) -> pd.DataFrame:
    """Calculate signed portfolio exposure by exchange."""
    return grouped_exposure(market_values, exchanges, nav).rename_axis(columns="exchange")


def sector_exposure(
    market_values: pd.DataFrame,
    sectors: pd.Series,
    nav: pd.Series | float,
) -> pd.DataFrame:
    """Calculate signed portfolio exposure by sector."""
    return grouped_exposure(market_values, sectors, nav).rename_axis(columns="sector")


def long_short_toolbox_report(
    market_values: pd.DataFrame,
    nav: pd.Series | float,
    beta: pd.Series | pd.DataFrame | None = None,
) -> dict[str, pd.Series]:
    """Return the core Chapter 8 exposure dashboard series."""
    counts = long_short_counts(market_values)
    report: dict[str, pd.Series] = {
        "gross_exposure": gross_exposure(market_values, nav),
        "net_exposure": net_exposure(market_values, nav),
        "concentration": concentration(market_values),
        "big_small_bet_ratio": big_small_bet_ratio(market_values),
        "long_count": counts["long_count"],
        "short_count": counts["short_count"],
    }
    if beta is not None:
        report["net_beta_exposure"] = net_beta_exposure(market_values, beta, nav)
    return report


def _divide_by_nav(numerator: pd.Series, nav: pd.Series | float) -> pd.Series:
    denominator = pd.Series(nav, index=numerator.index, dtype=float)
    if denominator.eq(0).any():
        raise ValueError("nav must be non-zero")
    return numerator.div(denominator)
