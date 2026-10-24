"""Crypto analytics: risk, correlation, DCA, perpetual-futures maths (research only)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from crypto.instruments import PERIODS_PER_YEAR


def risk_overview(close: pd.Series) -> dict[str, float]:
    """Annualised (365) volatility, return, drawdown from all-time high, and worst day."""
    c = pd.to_numeric(close, errors="coerce").dropna()
    if len(c) < 60 or (c <= 0).any():
        raise ValueError("At least 60 positive closes are needed.")
    r = c.pct_change().dropna()
    dd = c / c.cummax() - 1.0
    days = max((c.index[-1] - c.index[0]).days, 1)
    return {
        "annual_volatility": float(r.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)),
        "cagr": float((c.iloc[-1] / c.iloc[0]) ** (365.25 / days) - 1.0),
        "max_drawdown": float(dd.min()),
        "drawdown_from_high": float(dd.iloc[-1]),
        "worst_day": float(r.min()),
        "best_day": float(r.max()),
        "share_down_days": float((r < 0).mean()),
    }


def correlation(prices: pd.DataFrame, window: int | None = None) -> pd.DataFrame:
    rets = prices.pct_change().dropna(how="all")
    if window:
        rets = rets.tail(window)
    if len(rets) < 20:
        raise ValueError("At least 20 return observations are needed.")
    return rets.corr()


def dca_simulation(close: pd.Series, amount: float, every_days: int = 7) -> dict[str, float]:
    """Buy ``amount`` every ``every_days`` calendar days; compare with one lumpsum at the start."""
    c = pd.to_numeric(close, errors="coerce").dropna()
    if amount <= 0 or every_days < 1 or len(c) < 30:
        raise ValueError("amount > 0, every_days >= 1 and at least 30 prices required")
    dates = pd.date_range(c.index[0], c.index[-1], freq=f"{every_days}D")
    idx = c.index.searchsorted(dates, side="left")
    idx = np.unique(idx[idx < len(c)])
    buys = c.iloc[idx]
    units = float((amount / buys).sum())
    invested = amount * len(buys)
    final = units * float(c.iloc[-1])
    lump_final = invested / float(c.iloc[0]) * float(c.iloc[-1])
    return {
        "invested": invested,
        "final_value": final,
        "return": final / invested - 1.0,
        "average_cost": invested / units,
        "lumpsum_final_value": lump_final,
        "lumpsum_return": lump_final / invested - 1.0,
        "buys": float(len(buys)),
    }


# ----------------------------------------------------------------- perpetual futures maths
def liquidation_price(
    entry: float, leverage: float, *, long: bool = True, maintenance_margin: float = 0.005
) -> float:
    """Approximate liquidation price for an isolated-margin perpetual position.

    Long: entry * (1 - 1/L + mm); short: entry * (1 + 1/L - mm). Real exchanges add fees,
    tiered maintenance rates and funding, so treat this as optimistic.
    """
    if entry <= 0 or leverage < 1 or not 0 <= maintenance_margin < 1:
        raise ValueError("entry > 0, leverage >= 1 and maintenance_margin in [0, 1) required")
    if long:
        price = entry * (1.0 - 1.0 / leverage + maintenance_margin)
    else:
        price = entry * (1.0 + 1.0 / leverage - maintenance_margin)
    return max(price, 0.0)


def funding_cost(notional: float, rate_per_8h: float, days: float, *, long: bool = True) -> float:
    """Funding paid (positive) or received (negative) over ``days``; longs pay when rate > 0."""
    if notional < 0 or days < 0:
        raise ValueError("notional and days must be non-negative")
    paid = notional * rate_per_8h * 3.0 * days
    return paid if long else -paid


def position_size(balance: float, risk_pct: float, entry: float, stop: float) -> dict[str, float]:
    """Coin quantity so that hitting the stop loses ``risk_pct`` of the balance."""
    if balance <= 0 or not 0 < risk_pct <= 0.1 or entry <= 0 or stop <= 0 or entry == stop:
        raise ValueError("balance, entry, stop must be positive and differ; risk_pct in (0, 0.1]")
    quantity = balance * risk_pct / abs(entry - stop)
    return {
        "quantity": quantity,
        "notional": quantity * entry,
        "risk_amount": balance * risk_pct,
        "leverage_needed": quantity * entry / balance,
    }
