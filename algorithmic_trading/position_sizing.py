"""Expanded position-sizing methods for NSE/BSE strategy research."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSize:
    """Position-size result with the assumptions used to calculate it."""

    quantity: int
    risk_budget: float
    risk_per_share: float
    method: str


def atr_position_size(
    capital: float,
    risk_fraction: float,
    entry_price: float,
    atr: float,
    atr_multiple: float = 1.5,
) -> int:
    """Size a position so an ATR stop represents fixed account risk."""
    if capital <= 0 or risk_fraction <= 0:
        return 0
    if entry_price <= 0 or atr <= 0 or atr_multiple <= 0:
        return 0
    risk_budget = capital * risk_fraction
    risk_per_share = atr * atr_multiple
    return max(0, int(risk_budget // risk_per_share))


def fixed_fraction_size(
    capital: float,
    risk_fraction: float,
    entry_price: float,
) -> int:
    """Size by allocating a fixed fraction of capital to the position."""
    if capital <= 0 or risk_fraction <= 0 or entry_price <= 0:
        return 0
    return max(0, int((capital * risk_fraction) // entry_price))


def fixed_risk_size(
    capital: float,
    risk_fraction: float,
    entry_price: float,
    stop_price: float,
) -> PositionSize:
    """Size so the stop distance consumes the selected risk budget."""
    if capital <= 0 or risk_fraction <= 0 or entry_price <= 0:
        return PositionSize(0, 0.0, 0.0, "fixed_risk")

    risk_budget = capital * risk_fraction
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return PositionSize(0, risk_budget, 0.0, "fixed_risk")

    quantity = max(0, int(risk_budget // risk_per_share))
    return PositionSize(quantity, risk_budget, risk_per_share, "fixed_risk")


def volatility_size(
    capital: float,
    risk_fraction: float,
    volatility: float,
    price: float,
) -> PositionSize:
    """Size inversely to a supplied percentage volatility estimate."""
    if capital <= 0 or risk_fraction <= 0 or volatility <= 0 or price <= 0:
        return PositionSize(0, 0.0, 0.0, "volatility")

    risk_budget = capital * risk_fraction
    risk_per_share = price * volatility
    quantity = max(0, int(risk_budget // risk_per_share))
    return PositionSize(quantity, risk_budget, risk_per_share, "volatility")


def _valid_probability(value: float) -> bool:
    """Return whether a value is a finite probability strictly inside (0, 1)."""
    return math.isfinite(value) and 0.0 < value < 1.0


def fractional_kelly_fraction(
    win_probability: float,
    win_loss_ratio: float,
    fraction: float = 0.25,
) -> float:
    """Return a fractional Kelly allocation from measured trade statistics."""
    if not _valid_probability(win_probability):
        return 0.0
    if not math.isfinite(win_loss_ratio) or win_loss_ratio <= 0:
        return 0.0
    if not math.isfinite(fraction) or fraction <= 0 or fraction > 1:
        return 0.0

    loss_probability = 1.0 - win_probability
    full_kelly = win_probability - loss_probability / win_loss_ratio
    return max(0.0, full_kelly * fraction)


def capped_quantity(quantity: int, maximum: int | None = None) -> int:
    """Apply an optional hard quantity cap."""
    if quantity <= 0:
        return 0
    if maximum is None:
        return quantity
    if maximum <= 0:
        return 0
    return min(quantity, maximum)
