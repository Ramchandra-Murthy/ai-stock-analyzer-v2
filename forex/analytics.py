"""FX analytics: carry, currency strength, ATR in pips, correlation and trend snapshot."""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex.instruments import pip_size, split_pair


def daily_carry(base_rate: float, quote_rate: float, days: float = 1.0) -> float:
    """Return earned per unit of notional when LONG the pair for ``days`` calendar days.

    Long base earns the base rate and pays the quote rate. Rates are annual decimals. This is
    the interest-rate differential only; brokers add their own swap markups.
    """
    return (base_rate - quote_rate) * days / 365.0


def annual_carry(base_rate: float, quote_rate: float) -> float:
    return base_rate - quote_rate


def atr_pips(frame: pd.DataFrame, pair: str, period: int = 14) -> pd.Series:
    prev = frame["Close"].shift(1)
    tr = pd.concat(
        [frame["High"] - frame["Low"], (frame["High"] - prev).abs(), (frame["Low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean() / pip_size(pair)


def currency_strength(prices: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Trailing ``window``-bar strength of each currency from a set of pair prices.

    For every pair BASEQUOTE the pair return is credited to the base and debited from the
    quote; a currency's strength is its average credit over the pairs it appears in. Columns
    of ``prices`` must be six-letter pairs. Uses only data up to each bar.
    """
    if window < 2:
        raise ValueError("window must be at least 2")
    rets = prices.pct_change(window)
    currencies = sorted({c for p in prices.columns for c in split_pair(p)})
    out = pd.DataFrame(0.0, index=prices.index, columns=currencies)
    count = dict.fromkeys(currencies, 0)
    for pair in prices.columns:
        base, quote = split_pair(pair)
        out[base] += rets[pair].fillna(0.0)
        out[quote] -= rets[pair].fillna(0.0)
        count[base] += 1
        count[quote] += 1
    for c in currencies:
        out[c] /= count[c]
    return out.where(rets.notna().any(axis=1))


def correlation_matrix(prices: pd.DataFrame, window: int | None = None) -> pd.DataFrame:
    """Correlation of daily returns (last ``window`` bars if given)."""
    rets = prices.pct_change().dropna(how="all")
    if window:
        rets = rets.tail(window)
    if len(rets) < 20:
        raise ValueError("At least 20 return observations are needed.")
    return rets.corr()


def trend_snapshot(close: pd.Series, fast: int = 20, slow: int = 50) -> str:
    """ "Up", "Down" or "Range" from price vs two moving averages (last bar only)."""
    if len(close) < slow:
        raise ValueError("Not enough history.")
    f, s, last = (
        close.rolling(fast).mean().iloc[-1],
        close.rolling(slow).mean().iloc[-1],
        close.iloc[-1],
    )
    if last > f > s:
        return "Up"
    if last < f < s:
        return "Down"
    return "Range"


def pair_overview(prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pair in prices.columns:
        s = prices[pair].dropna()
        if len(s) < 60:
            continue
        rows.append(
            {
                "Pair": pair,
                "Last": float(s.iloc[-1]),
                "1D": float(s.iloc[-1] / s.iloc[-2] - 1),
                "1M": float(s.iloc[-1] / s.iloc[-22] - 1),
                "3M": float(s.iloc[-1] / s.iloc[-64] - 1) if len(s) > 64 else np.nan,
                "Annual vol": float(s.pct_change().std(ddof=1) * np.sqrt(252)),
                "Trend": trend_snapshot(s),
            }
        )
    if not rows:
        raise ValueError("No pair had enough history.")
    return pd.DataFrame(rows).set_index("Pair")
