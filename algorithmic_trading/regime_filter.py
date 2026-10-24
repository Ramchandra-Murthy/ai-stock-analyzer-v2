"""Causal market-regime gates for systematic strategies.

A gate is a boolean series: True when conditions are "risk-on" and a strategy may hold
positions, False when it should stand aside. Every value at bar *t* is computed from data
up to and including *t* only. Combined with the backtester (a signal at *t* trades bar
*t+1*), a gate adds no look-ahead.

Gates are research tools, not guarantees: they usually trade a smaller drawdown for lower
return and they can lag turning points.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
REGIME_MODES = ("Trend (50/200-day)", "Calm volatility", "Trend + calm volatility")


def trend_gate(close: pd.Series, fast: int = 50, slow: int = 200) -> pd.Series:
    """True when price is above the slow average and the fast average is above the slow one.

    The first ``slow - 1`` bars are False: not enough history to call the trend.
    """
    if fast < 2 or slow <= fast:
        raise ValueError("need 2 <= fast < slow")
    close = pd.to_numeric(close, errors="coerce")
    fast_ma = close.rolling(fast, min_periods=fast).mean()
    slow_ma = close.rolling(slow, min_periods=slow).mean()
    return ((close > slow_ma) & (fast_ma > slow_ma)).fillna(False).astype(bool)


def realised_volatility(close: pd.Series, window: int = 20) -> pd.Series:
    """Annualised rolling standard deviation of daily returns."""
    returns = pd.to_numeric(close, errors="coerce").pct_change()
    return returns.rolling(window, min_periods=window).std(ddof=1) * np.sqrt(TRADING_DAYS)


def calm_volatility_gate(
    close: pd.Series, window: int = 20, lookback: int = 252, quantile: float = 0.8
) -> pd.Series:
    """True when volatility is below its own trailing ``quantile`` (not in a stress spike).

    The threshold is the quantile of the *preceding* ``lookback`` volatility readings
    (shifted one bar), so a spike cannot raise its own bar's threshold. Bars without enough
    history are False.
    """
    if not 0.0 < quantile < 1.0:
        raise ValueError("quantile must be between 0 and 1")
    vol = realised_volatility(close, window)
    threshold = vol.shift(1).rolling(lookback, min_periods=max(lookback // 2, 2)).quantile(quantile)
    return (vol <= threshold).fillna(False).astype(bool)


def level_gate(
    series: pd.Series, *, below: float | None = None, above: float | None = None
) -> pd.Series:
    """Gate on an external level such as India VIX (True while it is below/above a level)."""
    if below is None and above is None:
        raise ValueError("give below= or above=")
    values = pd.to_numeric(series, errors="coerce")
    gate = pd.Series(True, index=values.index)
    if below is not None:
        gate &= values < below
    if above is not None:
        gate &= values > above
    return (gate & values.notna()).astype(bool)


def regime_gate(close: pd.Series, mode: str = REGIME_MODES[0]) -> pd.Series:
    """The named gate (see ``REGIME_MODES``), aligned to ``close``."""
    if mode == REGIME_MODES[0]:
        return trend_gate(close)
    if mode == REGIME_MODES[1]:
        return calm_volatility_gate(close)
    if mode == REGIME_MODES[2]:
        return trend_gate(close) & calm_volatility_gate(close)
    raise ValueError(f"Unknown regime mode: {mode}")


def apply_regime_gate(signals: pd.Series, gate: pd.Series) -> pd.Series:
    """Zero out the signal on bars where the gate is False (missing gate bars count as off)."""
    aligned = gate.reindex(signals.index).fillna(False).astype(bool)
    return signals.where(aligned, 0.0)


def regime_share(gate: pd.Series) -> float:
    """Fraction of bars with the gate on."""
    return float(gate.mean()) if len(gate) else 0.0
