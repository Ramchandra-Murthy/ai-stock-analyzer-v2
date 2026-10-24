"""Integrated Chapter 4-10 trading workflow.

This module connects the independently tested regime, edge, position-sizing,
portfolio-risk, and journal components into one auditable snapshot. It does
not replace the underlying analytics and does not place trades.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from engine.long_short_toolbox import risk_appetite
from engine.position_sizing import fixed_risk_size
from engine.regime_engine import chapter4_regime, latest_regime
from engine.trading_edge import trend_following_signal


def integrated_trade_snapshot(
    prices: pd.DataFrame,
    *,
    capital: float,
    risk_fraction: float,
    stop_price: float,
    equity_curve: pd.Series,
    journal_score: float | None = None,
    regime_threshold: int = 3,
    fast_period: int = 20,
    slow_period: int = 50,
    max_drawdown_tolerance: float = -0.05,
    min_risk: float = 0.25,
    max_risk: float = 1.0,
) -> dict[str, Any]:
    """Build one auditable decision snapshot from Chapters 4-10 components.

    The result reports regime, directional edge, risk appetite, position size,
    and optional journal completeness. It deliberately stops at analytics:
    callers decide whether and how to execute a trade.
    """
    if prices.empty:
        raise ValueError("prices must not be empty")
    if "Close" not in prices.columns:
        raise KeyError("prices must contain a Close column")
    if len(prices) < slow_period:
        raise ValueError("prices does not contain enough bars for the edge signal")

    regime = latest_regime(prices, regime_threshold=regime_threshold)
    edge = trend_following_signal(
        prices["Close"],
        fast_period=fast_period,
        slow_period=slow_period,
    )
    edge_value = float(edge.iloc[-1])
    appetite = risk_appetite(
        equity_curve,
        max_drawdown_tolerance=max_drawdown_tolerance,
        min_risk=min_risk,
        max_risk=max_risk,
    )
    risk_multiplier = float(appetite.iloc[-1])
    base_units = fixed_risk_size(
        capital,
        risk_fraction,
        float(prices["Close"].iloc[-1]),
        stop_price,
    )
    sized_units = base_units * risk_multiplier

    regime_value = str(regime.get("regime", "INSUFFICIENT DATA"))
    regime_score = float(regime.get("regime_score", 0))
    direction = "LONG" if edge_value > 0 else "SHORT" if edge_value < 0 else "FLAT"

    return {
        "regime": regime_value,
        "regime_score": regime_score,
        "edge_signal": edge_value,
        "direction": direction,
        "risk_appetite": risk_multiplier,
        "base_position_size": base_units,
        "adjusted_position_size": sized_units,
        "journal_score": journal_score,
    }


def integrated_trade_frame(
    prices: pd.DataFrame,
    *,
    fast_period: int = 20,
    slow_period: int = 50,
    regime_threshold: int = 3,
) -> pd.DataFrame:
    """Return a per-bar integration frame for scanner/dashboard consumption."""
    if prices.empty:
        return pd.DataFrame(columns=["close", "edge_signal", "regime_score", "regime"])
    if "Close" not in prices.columns:
        raise KeyError("prices must contain a Close column")
    if len(prices) < slow_period:
        raise ValueError("prices does not contain enough bars for the edge signal")

    regime = chapter4_regime(prices, regime_threshold=regime_threshold)
    edge = trend_following_signal(prices["Close"], fast_period=fast_period, slow_period=slow_period)
    return pd.DataFrame(
        {
            "close": pd.to_numeric(prices["Close"], errors="coerce"),
            "edge_signal": edge,
            "regime_score": regime["regime_score"],
            "regime": regime["regime"],
        },
        index=prices.index,
    )
