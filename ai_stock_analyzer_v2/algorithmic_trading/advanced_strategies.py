"""Systematic strategy library: trend, breakout, mean-reversion, momentum and sizing.

Every signal function returns a ``pd.Series`` of target positions in {-1, 0, +1} indexed
like its input. A signal at bar *t* uses only data up to and including the close of bar
*t*; ``algorithmic_trading.backtester.run_backtest`` applies it to the *next* bar's return,
so there is no look-ahead. Warm-up bars (not enough history yet) are 0.

These are research tools. Backtested results are not forecasts, and none of this places
orders.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"price frame is missing required columns: {missing}")


def _positive_int(value: int, name: str) -> int:
    if int(value) != value or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def average_true_range(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's ATR (exponential smoothing with alpha = 1/period).

    Returns NaN until ``period`` bars are available. Does not modify ``frame``.
    """
    period = _positive_int(period, "period")
    _require_columns(frame, ("High", "Low", "Close"))
    high, low, close = (_numeric(frame[c]) for c in ("High", "Low", "Close"))
    previous_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0.0)).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    relative_strength = gain / loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + relative_strength)
    # Gains with no losses means RSI is 100; no movement at all stays undefined (NaN).
    return rsi.where(~((loss == 0.0) & (gain > 0.0)), 100.0)


# --------------------------------------------------------------------------------------
# trend following
# --------------------------------------------------------------------------------------
def supertrend(frame: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """ATR-band trend indicator.

    Returns columns ``supertrend`` (the active stop line) and ``direction`` (+1 uptrend,
    -1 downtrend, 0 during warm-up). The direction flips only when the close crosses the
    opposite band, which makes it a trailing-stop trend filter.
    """
    period = _positive_int(period, "period")
    if not np.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("multiplier must be a positive number")
    _require_columns(frame, ("High", "Low", "Close"))

    high, low, close = (_numeric(frame[c]).to_numpy() for c in ("High", "Low", "Close"))
    atr = average_true_range(frame, period).to_numpy()
    midpoint = (high + low) / 2.0
    basic_upper = midpoint + multiplier * atr
    basic_lower = midpoint - multiplier * atr

    size = len(frame)
    final_upper = np.full(size, np.nan)
    final_lower = np.full(size, np.nan)
    direction = np.zeros(size, dtype=int)
    line = np.full(size, np.nan)

    started = False
    for i in range(size):
        if not (np.isfinite(atr[i]) and np.isfinite(close[i])):
            continue
        if not started:
            final_upper[i], final_lower[i] = basic_upper[i], basic_lower[i]
            direction[i] = 1 if close[i] >= midpoint[i] else -1
            started = True
        else:
            prev = i - 1
            final_upper[i] = (
                basic_upper[i]
                if basic_upper[i] < final_upper[prev] or close[prev] > final_upper[prev]
                else final_upper[prev]
            )
            final_lower[i] = (
                basic_lower[i]
                if basic_lower[i] > final_lower[prev] or close[prev] < final_lower[prev]
                else final_lower[prev]
            )
            if close[i] > final_upper[prev]:
                direction[i] = 1
            elif close[i] < final_lower[prev]:
                direction[i] = -1
            else:
                direction[i] = direction[prev]
        line[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

    return pd.DataFrame({"supertrend": line, "direction": direction}, index=frame.index)


def supertrend_signals(
    frame: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
    allow_short: bool = False,
) -> pd.Series:
    """Long while Supertrend is up; flat (or short if ``allow_short``) while it is down."""
    direction = supertrend(frame, period, multiplier)["direction"]
    if not allow_short:
        direction = direction.clip(lower=0)
    return direction.astype(float)


# --------------------------------------------------------------------------------------
# breakout
# --------------------------------------------------------------------------------------
def donchian_breakout_signals(
    frame: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    allow_short: bool = False,
) -> pd.Series:
    """Turtle-style channel breakout.

    Enter long when the close exceeds the highest high of the previous ``entry_window``
    bars; exit when it falls below the lowest low of the previous ``exit_window`` bars.
    With ``allow_short`` the mirror-image rules apply. Channels use *previous* bars only.
    """
    entry_window = _positive_int(entry_window, "entry_window")
    exit_window = _positive_int(exit_window, "exit_window")
    _require_columns(frame, ("High", "Low", "Close"))

    close = _numeric(frame["Close"]).to_numpy()
    entry_high = _numeric(frame["High"]).rolling(entry_window).max().shift(1).to_numpy()
    entry_low = _numeric(frame["Low"]).rolling(entry_window).min().shift(1).to_numpy()
    exit_high = _numeric(frame["High"]).rolling(exit_window).max().shift(1).to_numpy()
    exit_low = _numeric(frame["Low"]).rolling(exit_window).min().shift(1).to_numpy()

    position = np.zeros(len(frame))
    state = 0
    for i in range(len(frame)):
        c = close[i]
        if not np.isfinite(c):
            position[i] = state
            continue
        if state == 0:
            if np.isfinite(entry_high[i]) and c > entry_high[i]:
                state = 1
            elif allow_short and np.isfinite(entry_low[i]) and c < entry_low[i]:
                state = -1
        elif state == 1:
            if np.isfinite(exit_low[i]) and c < exit_low[i]:
                state = 0
                if allow_short and np.isfinite(entry_low[i]) and c < entry_low[i]:
                    state = -1
        elif state == -1:
            if np.isfinite(exit_high[i]) and c > exit_high[i]:
                state = 0
                if np.isfinite(entry_high[i]) and c > entry_high[i]:
                    state = 1
        position[i] = state
    return pd.Series(position, index=frame.index, dtype=float)


# --------------------------------------------------------------------------------------
# mean reversion
# --------------------------------------------------------------------------------------
def zscore_mean_reversion_signals(
    close: pd.Series,
    window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    allow_short: bool = False,
) -> pd.Series:
    """Fade stretched prices: long below -entry_z, flat once the z-score recovers.

    ``z = (close - rolling mean) / rolling std``. A long is held until ``z`` rises above
    ``-exit_z``. With ``allow_short`` the mirror-image applies above +entry_z.
    """
    window = _positive_int(window, "window")
    if window < 2:
        raise ValueError("window must be at least 2")
    if entry_z <= 0 or exit_z < 0 or exit_z >= entry_z:
        raise ValueError("require 0 <= exit_z < entry_z")

    prices = _numeric(close)
    mean = prices.rolling(window).mean()
    std = prices.rolling(window).std(ddof=1)
    z = ((prices - mean) / std.replace(0.0, np.nan)).to_numpy()

    position = np.zeros(len(prices))
    state = 0
    for i, value in enumerate(z):
        if np.isfinite(value):
            if state == 0:
                if value <= -entry_z:
                    state = 1
                elif allow_short and value >= entry_z:
                    state = -1
            elif state == 1 and value >= -exit_z:
                state = 0
            elif state == -1 and value <= exit_z:
                state = 0
        position[i] = state
    return pd.Series(position, index=prices.index, dtype=float)


def rsi2_pullback_signals(
    close: pd.Series,
    rsi_period: int = 2,
    oversold: float = 10.0,
    trend_window: int = 200,
    exit_window: int = 5,
) -> pd.Series:
    """Buy short-term pullbacks inside a long-term uptrend (Connors-style RSI(2)).

    Enter long when RSI(``rsi_period``) is below ``oversold`` and the close is above its
    ``trend_window`` average; exit when the close rises above its ``exit_window`` average.
    Long-only by design.
    """
    rsi_period = _positive_int(rsi_period, "rsi_period")
    trend_window = _positive_int(trend_window, "trend_window")
    exit_window = _positive_int(exit_window, "exit_window")
    prices = _numeric(close)

    rsi = _rsi(prices, rsi_period).to_numpy()
    trend = prices.rolling(trend_window).mean().to_numpy()
    exit_average = prices.rolling(exit_window).mean().to_numpy()
    values = prices.to_numpy()

    position = np.zeros(len(prices))
    state = 0
    for i in range(len(prices)):
        if np.isfinite(values[i]):
            if state == 0:
                if (
                    np.isfinite(rsi[i])
                    and np.isfinite(trend[i])
                    and rsi[i] < oversold
                    and values[i] > trend[i]
                ):
                    state = 1
            elif np.isfinite(exit_average[i]) and values[i] > exit_average[i]:
                state = 0
        position[i] = state
    return pd.Series(position, index=prices.index, dtype=float)


# --------------------------------------------------------------------------------------
# momentum across a universe
# --------------------------------------------------------------------------------------
def momentum_scores(prices: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.Series:
    """Cross-sectional momentum: return from ``lookback`` bars ago to ``skip`` bars ago.

    Skipping the most recent month avoids the short-term reversal effect. ``prices`` has
    one column per symbol. Symbols without enough history get NaN.
    """
    lookback = _positive_int(lookback, "lookback")
    if int(skip) != skip or skip < 0 or skip >= lookback:
        raise ValueError("skip must be a non-negative integer smaller than lookback")
    if len(prices) <= lookback:
        return pd.Series(np.nan, index=prices.columns, dtype=float)
    numeric = prices.apply(pd.to_numeric, errors="coerce")
    recent = numeric.iloc[-1 - skip]
    past = numeric.iloc[-1 - lookback]
    return (recent / past - 1.0).where(past > 0)


def top_momentum_weights(
    prices: pd.DataFrame,
    top_n: int = 5,
    lookback: int = 252,
    skip: int = 21,
    require_positive: bool = True,
) -> pd.Series:
    """Equal weights on the ``top_n`` momentum leaders (all zero if none qualify).

    With ``require_positive`` a symbol must also have positive momentum (absolute momentum
    filter), so the portfolio goes to cash when nothing is trending up.
    """
    top_n = _positive_int(top_n, "top_n")
    scores = momentum_scores(prices, lookback, skip).dropna()
    if require_positive:
        scores = scores[scores > 0]
    leaders = scores.sort_values(ascending=False).head(top_n)
    weights = pd.Series(0.0, index=prices.columns)
    if not leaders.empty:
        weights.loc[leaders.index] = 1.0 / len(leaders)
    return weights


# --------------------------------------------------------------------------------------
# combining and sizing
# --------------------------------------------------------------------------------------
def ensemble_vote(signals: dict[str, pd.Series], threshold: float = 0.5) -> pd.Series:
    """Combine strategies: long if the average signal >= threshold, short if <= -threshold.

    Averaging independent strategies tends to smooth out the whipsaws of any single one.
    """
    if not signals:
        raise ValueError("at least one signal series is required")
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    frame = pd.concat({name: _numeric(series) for name, series in signals.items()}, axis=1)
    average = frame.mean(axis=1)
    combined = pd.Series(0.0, index=frame.index)
    combined[average >= threshold] = 1.0
    combined[average <= -threshold] = -1.0
    return combined


def volatility_target_scale(
    prices: pd.Series,
    target_volatility: float = 0.15,
    window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Position scale in [0, max_leverage] that targets a constant annualised volatility.

    Uses realised volatility measured through the *previous* bar, so it is safe to multiply
    with a signal and backtest. Quiet markets get a larger scale, turbulent ones a smaller
    one. Warm-up bars are 0.
    """
    window = _positive_int(window, "window")
    if window < 2:
        raise ValueError("window must be at least 2")
    if target_volatility <= 0 or max_leverage <= 0:
        raise ValueError("target_volatility and max_leverage must be positive")
    returns = _numeric(prices).pct_change()
    realised = returns.rolling(window).std(ddof=1).shift(1) * np.sqrt(TRADING_DAYS)
    scale = (target_volatility / realised.replace(0.0, np.nan)).clip(upper=max_leverage)
    return scale.fillna(0.0).clip(lower=0.0)
