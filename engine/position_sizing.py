"""Position-sizing utilities inspired by Chapter 6.

Provides deterministic fixed-allocation, fixed-risk, volatility and
Kelly-based sizing primitives for use by trading and portfolio engines.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def fixed_dollar_size(capital: float, allocation: float, price: float) -> float:
    """Return shares/contracts for a fixed dollar allocation."""
    _validate_positive(capital, "capital")
    _validate_fraction(allocation, "allocation")
    _validate_positive(price, "price")
    return float(capital * allocation / price)


def fixed_risk_size(
    capital: float,
    risk_fraction: float,
    entry_price: float,
    stop_price: float,
) -> float:
    """Size a position so the stop loss risks a fixed fraction of capital."""
    _validate_positive(capital, "capital")
    _validate_fraction(risk_fraction, "risk_fraction")
    _validate_positive(entry_price, "entry_price")
    _validate_positive(stop_price, "stop_price")
    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0:
        raise ValueError("entry_price and stop_price must differ")
    return float(capital * risk_fraction / risk_per_unit)


def volatility_size(
    capital: float,
    target_volatility: float,
    asset_volatility: float,
    price: float,
) -> float:
    """Return units sized to target a fraction of portfolio volatility."""
    _validate_positive(capital, "capital")
    _validate_positive(target_volatility, "target_volatility")
    _validate_positive(asset_volatility, "asset_volatility")
    _validate_positive(price, "price")
    return float(capital * target_volatility / (asset_volatility * price))


def atr_position_size(
    capital: float,
    risk_fraction: float,
    atr: float,
    atr_multiple: float = 1.0,
) -> float:
    """Return units from fixed risk divided by an ATR-based risk unit."""
    _validate_positive(capital, "capital")
    _validate_fraction(risk_fraction, "risk_fraction")
    _validate_positive(atr, "atr")
    _validate_positive(atr_multiple, "atr_multiple")
    return float(capital * risk_fraction / (atr * atr_multiple))


def kelly_position_size(
    capital: float,
    kelly_fraction: float,
    price: float,
    max_fraction: float | None = None,
) -> float:
    """Return units from a Kelly allocation, optionally capped."""
    _validate_positive(capital, "capital")
    _validate_positive(price, "price")
    if kelly_fraction < 0:
        raise ValueError("kelly_fraction must be non-negative")
    fraction = kelly_fraction
    if max_fraction is not None:
        _validate_fraction(max_fraction, "max_fraction")
        fraction = min(fraction, max_fraction)
    return float(capital * fraction / price)


def rolling_volatility(returns: pd.Series, window: int = 20, annualize: bool = True) -> pd.Series:
    """Calculate rolling standard deviation of returns."""
    if window < 2:
        raise ValueError("window must be at least 2")
    values = pd.to_numeric(returns, errors="coerce")
    result = values.rolling(window, min_periods=window).std()
    if annualize:
        result = result * np.sqrt(252.0)
    return result.rename("rolling_volatility")


def average_true_range(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Calculate Wilder-style ATR from true range using a rolling mean."""
    if window < 1:
        raise ValueError("window must be at least 1")
    high_values = pd.to_numeric(high, errors="coerce")
    low_values = pd.to_numeric(low, errors="coerce")
    close_values = pd.to_numeric(close, errors="coerce")
    previous_close = close_values.shift(1)
    true_range = pd.concat(
        [
            high_values - low_values,
            (high_values - previous_close).abs(),
            (low_values - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window, min_periods=window).mean().rename("atr")


def position_sizing_report(
    capital: float,
    price: float,
    risk_fraction: float,
    stop_price: float,
    atr: float,
    asset_volatility: float,
    kelly_fraction: float,
) -> dict[str, float]:
    """Return a compact comparison of Chapter 6 sizing methods."""
    return {
        "fixed_dollar": fixed_dollar_size(capital, risk_fraction, price),
        "fixed_risk": fixed_risk_size(capital, risk_fraction, price, stop_price),
        "atr": atr_position_size(capital, risk_fraction, atr),
        "volatility": volatility_size(capital, risk_fraction, asset_volatility, price),
        "kelly": kelly_position_size(capital, kelly_fraction, price),
    }


def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _validate_fraction(value: float, name: str) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
