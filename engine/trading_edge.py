"""Trading-edge analytics inspired by Chapter 5 of the book.

The module focuses on gain expectancy and the two strategy archetypes
described in the chapter: trend following and mean reversion. It is
dependency-light so the scanner can reuse the functions without a
specialised statistics stack.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def arithmetic_expectancy(
    win_rate: float,
    average_win: float,
    average_loss: float,
) -> float:
    """Return arithmetic gain expectancy per trade.

    average_loss is expected to be negative, matching the book's
    expectancy formulation.
    """
    _validate_probability(win_rate)
    return float(win_rate * average_win + (1.0 - win_rate) * average_loss)


def geometric_expectancy(
    win_rate: float,
    average_win: float,
    average_loss: float,
) -> float:
    """Return geometric gain expectancy for compounding returns."""
    _validate_probability(win_rate)
    if average_win <= -1 or average_loss <= -1:
        raise ValueError("returns must be greater than -100%")
    return float((1.0 + average_win) ** win_rate * (1.0 + average_loss) ** (1.0 - win_rate) - 1.0)


def kelly_fraction(
    win_rate: float,
    average_win: float,
    average_loss: float,
) -> float:
    """Return the Kelly fraction from win rate, average win and loss."""
    _validate_probability(win_rate)
    if average_win <= 0:
        raise ValueError("average_win must be positive")
    if average_loss >= 0:
        raise ValueError("average_loss must be negative")
    return float(win_rate / abs(average_loss) - (1.0 - win_rate) / average_win)


def trade_statistics(returns: pd.Series) -> dict[str, float]:
    """Calculate win rate, average win/loss and expectancy from trade returns."""
    values = pd.to_numeric(returns, errors="coerce").dropna()
    if values.empty:
        return {
            "trades": 0.0,
            "win_rate": float("nan"),
            "average_win": float("nan"),
            "average_loss": float("nan"),
            "arithmetic_expectancy": float("nan"),
            "geometric_expectancy": float("nan"),
            "kelly_fraction": float("nan"),
        }

    wins = values[values > 0]
    losses = values[values < 0]
    win_rate = float((values > 0).mean())
    average_win = float(wins.mean()) if not wins.empty else 0.0
    average_loss = float(losses.mean()) if not losses.empty else 0.0

    return {
        "trades": float(len(values)),
        "win_rate": win_rate,
        "average_win": average_win,
        "average_loss": average_loss,
        "arithmetic_expectancy": arithmetic_expectancy(win_rate, average_win, average_loss),
        "geometric_expectancy": (
            geometric_expectancy(win_rate, average_win, average_loss)
            if average_win > -1 and average_loss > -1
            else float("nan")
        ),
        "kelly_fraction": (
            kelly_fraction(win_rate, average_win, average_loss)
            if average_win > 0 and average_loss < 0
            else float("nan")
        ),
    }


def trend_following_signal(
    close: pd.Series,
    fast_period: int = 20,
    slow_period: int = 50,
) -> pd.Series:
    """Generate a simple trend-following signal from moving-average direction."""
    _validate_periods(fast_period, slow_period)
    prices = pd.to_numeric(close, errors="coerce")
    fast = prices.rolling(fast_period, min_periods=fast_period).mean()
    slow = prices.rolling(slow_period, min_periods=slow_period).mean()
    return pd.Series(np.sign(fast - slow), index=close.index, name="trend_signal")


def mean_reversion_signal(
    close: pd.Series,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
) -> pd.Series:
    """Generate a mean-reversion signal from rolling price z-score.

    A sufficiently low z-score is bullish (+1); a sufficiently high z-score
    is bearish (-1); values inside the exit band are neutral (0).
    """
    if window < 2:
        raise ValueError("window must be at least 2")
    if entry_z <= 0 or exit_z < 0 or exit_z >= entry_z:
        raise ValueError("require entry_z > exit_z >= 0")

    prices = pd.to_numeric(close, errors="coerce")
    mean = prices.rolling(window, min_periods=window).mean()
    std = prices.rolling(window, min_periods=window).std()
    zscore = (prices - mean).div(std.replace(0, np.nan))

    signal = pd.Series(0.0, index=close.index, name="mean_reversion_signal")
    signal.loc[zscore <= -entry_z] = 1.0
    signal.loc[zscore >= entry_z] = -1.0
    return signal


def pair_zscore(
    first: pd.Series,
    second: pd.Series,
    window: int = 60,
    use_ratio: bool = True,
) -> pd.Series:
    """Standardise a pair spread or ratio over a rolling window."""
    if window < 2:
        raise ValueError("window must be at least 2")
    left = pd.to_numeric(first, errors="coerce")
    right = pd.to_numeric(second, errors="coerce")
    if use_ratio:
        spread = left.div(right.replace(0, np.nan))
    else:
        spread = left - right

    mean = spread.rolling(window, min_periods=window).mean()
    std = spread.rolling(window, min_periods=window).std()
    return ((spread - mean) / std.replace(0, np.nan)).rename("pair_zscore")


def pairs_trading_signal(
    zscore: pd.Series,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
) -> pd.Series:
    """Generate a systematic pair-trading direction from z-score."""
    if entry_z <= 0 or exit_z < 0 or exit_z >= entry_z:
        raise ValueError("require entry_z > exit_z >= 0")

    score = pd.to_numeric(zscore, errors="coerce")
    signal = pd.Series(0.0, index=zscore.index, name="pairs_signal")
    signal.loc[score >= entry_z] = -1.0
    signal.loc[score <= -entry_z] = 1.0
    return signal


def trading_edge_report(returns: pd.Series) -> dict[str, Any]:
    """Return a compact Chapter 5 trading-edge report."""
    stats = trade_statistics(returns)
    if not stats["trades"]:
        return {"strategy_type": "INSUFFICIENT DATA", **stats}

    strategy_type = "TREND FOLLOWING" if stats["win_rate"] < 0.5 else "MEAN REVERSION"
    return {"strategy_type": strategy_type, **stats}


def _validate_probability(value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError("win_rate must be between 0 and 1")


def _validate_periods(fast_period: int, slow_period: int) -> None:
    if fast_period < 2 or slow_period < 2:
        raise ValueError("moving-average periods must be at least 2")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")
