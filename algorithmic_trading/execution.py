"""Execution analytics: slicing schedules, stylised market impact and implementation shortfall.

Research only. Splitting a large order over time lowers market impact but exposes it to price
drift; this module quantifies both on a price/volume path you supply (for example one real
intraday session). The impact model is the widely used square-root law,
``impact = k * daily_volatility * sqrt(shares / average_daily_volume)``, applied per slice, so
it is a stylised estimate and not a prediction of what a broker will fill.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BUY = "buy"
SELL = "sell"


def _check_side(side: str) -> int:
    if side not in (BUY, SELL):
        raise ValueError("side must be 'buy' or 'sell'.")
    return 1 if side == BUY else -1


def _apportion(total: int, weights: np.ndarray) -> np.ndarray:
    """Split ``total`` whole shares by ``weights`` (largest remainder; sums exactly)."""
    w = np.asarray(weights, dtype=float)
    if total < 0 or w.size == 0 or not np.all(np.isfinite(w)) or (w < 0).any() or w.sum() <= 0:
        raise ValueError("Need a non-negative share count and positive finite weights.")
    exact = total * w / w.sum()
    base = np.floor(exact).astype(int)
    order = np.argsort(-(exact - base), kind="stable")
    base[order[: total - int(base.sum())]] += 1
    return np.asarray(base, dtype=int)


def u_shaped_profile(slices: int) -> np.ndarray:
    """Typical intraday volume curve: heavy at the open and close, light at midday."""
    if slices < 1:
        raise ValueError("slices must be at least 1.")
    x = np.linspace(-1.0, 1.0, slices)
    profile = 1.0 + 1.5 * x**2
    return np.asarray(profile / profile.sum(), dtype=float)


def twap_schedule(shares: int, slices: int) -> np.ndarray:
    """Equal shares per slice."""
    if slices < 1:
        raise ValueError("slices must be at least 1.")
    return _apportion(int(shares), np.ones(slices))


def vwap_schedule(shares: int, volume_profile) -> np.ndarray:
    """Shares in proportion to the expected volume in each slice."""
    return _apportion(int(shares), np.asarray(volume_profile, dtype=float))


def pov_schedule(shares: int, volumes, participation: float) -> np.ndarray:
    """Trade ``participation`` of each slice's volume until done; may leave a remainder."""
    if not 0 < participation <= 0.5:
        raise ValueError("participation must be in (0, 0.5].")
    vols = np.asarray(volumes, dtype=float)
    if (vols < 0).any() or not np.all(np.isfinite(vols)):
        raise ValueError("volumes must be finite and non-negative.")
    remaining, out = int(shares), np.zeros(len(vols), dtype=int)
    for i, volume in enumerate(vols):
        take = min(remaining, int(participation * volume))
        out[i], remaining = take, remaining - take
    return out


def square_root_impact(shares: float, adv: float, daily_vol: float, k: float = 0.5) -> float:
    """Expected price impact as a fraction of price for trading ``shares``."""
    if shares < 0 or adv <= 0 or daily_vol < 0 or k < 0:
        raise ValueError("shares, volatility and k must be >= 0 and adv > 0.")
    return float(k * daily_vol * np.sqrt(shares / adv))


@dataclass(frozen=True)
class ExecutionResult:
    side: str
    requested: int
    filled: int
    average_price: float
    arrival_price: float
    shortfall_bps: float  # implementation shortfall vs arrival, positive = worse for you
    shortfall_rupees: float
    impact_bps: float  # model impact only (excludes spread and drift)
    spread_bps: float
    drift_bps: float  # market move between arrival and the fill times
    vs_vwap_bps: float  # versus the session's volume-weighted price, positive = worse
    fills: pd.DataFrame


def simulate_execution(
    side: str,
    schedule,
    prices,
    volumes,
    *,
    adv: float,
    daily_vol: float,
    k: float = 0.5,
    half_spread_bps: float = 2.0,
    arrival_price: float | None = None,
) -> ExecutionResult:
    """Fill ``schedule`` along ``prices``; each slice pays half the spread plus impact."""
    sign = _check_side(side)
    q = np.asarray(schedule, dtype=float)
    px = np.asarray(prices, dtype=float)
    vol = np.asarray(volumes, dtype=float)
    if not (len(q) == len(px) == len(vol)) or len(q) == 0:
        raise ValueError("schedule, prices and volumes must have the same non-zero length.")
    if not np.all(np.isfinite(px)) or (px <= 0).any():
        raise ValueError("prices must be positive and finite.")
    if q.sum() <= 0:
        raise ValueError("The schedule fills no shares.")
    arrival = float(px[0] if arrival_price is None else arrival_price)
    impact = np.array([square_root_impact(x, adv, daily_vol, k) for x in q])
    spread = half_spread_bps / 10_000.0
    fill_px = px * (1.0 + sign * (impact + spread))
    filled = float(q.sum())
    avg = float((q * fill_px).sum() / filled)
    shortfall = sign * (avg - arrival) / arrival
    drift = sign * float((q * (px - arrival)).sum() / filled) / arrival
    impact_part = float((q * impact).sum() / filled)
    session = float((px * vol).sum() / vol.sum()) if vol.sum() > 0 else float(px.mean())
    fills = pd.DataFrame(
        {
            "shares": q.astype(int),
            "market_price": px,
            "fill_price": fill_px,
            "impact_bps": impact * 10_000.0,
        }
    )
    return ExecutionResult(
        side=side,
        requested=int(round(float(q.sum()))),
        filled=int(round(filled)),
        average_price=avg,
        arrival_price=arrival,
        shortfall_bps=shortfall * 10_000.0,
        shortfall_rupees=sign * float((q * (fill_px - arrival)).sum()),
        impact_bps=impact_part * 10_000.0,
        spread_bps=half_spread_bps,
        drift_bps=drift * 10_000.0,
        vs_vwap_bps=sign * (avg - session) / session * 10_000.0,
        fills=fills,
    )
