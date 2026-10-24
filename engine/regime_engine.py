"""Regime classification helpers inspired by the book's Chapter 4.

States are +1 bullish, -1 bearish, 0 neutral/insufficient history.
The functions are pure so they can be reused by the NSE/BSE scanner.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def regime_breakout(
    df: pd.DataFrame,
    high_column: str = "High",
    low_column: str = "Low",
    periods: int = 50,
) -> pd.Series:
    """Fresh rolling high -> +1; fresh rolling low -> -1; otherwise carry state."""
    if periods < 2:
        raise ValueError("periods must be at least 2")
    if high_column not in df.columns or low_column not in df.columns:
        raise KeyError(f"Missing required columns: {high_column}, {low_column}")

    highs = pd.to_numeric(df[high_column], errors="coerce")
    lows = pd.to_numeric(df[low_column], errors="coerce")
    states = np.where(
        highs.eq(highs.rolling(periods, min_periods=periods).max()),
        1.0,
        np.where(
            lows.eq(lows.rolling(periods, min_periods=periods).min()),
            -1.0,
            np.nan,
        ),
    )
    return pd.Series(states, index=df.index, name=f"breakout_{periods}").ffill()


def regime_sma(
    df: pd.DataFrame,
    close_column: str = "Close",
    short_period: int = 20,
    long_period: int = 50,
) -> pd.Series:
    """Return the sign of short SMA minus long SMA."""
    _validate_periods(short_period, long_period)
    close = pd.to_numeric(df[close_column], errors="coerce")
    short = close.rolling(short_period, min_periods=short_period).mean()
    long = close.rolling(long_period, min_periods=long_period).mean()
    return pd.Series(np.sign(short - long), index=df.index, name="sma_regime")


def regime_ema(
    df: pd.DataFrame,
    close_column: str = "Close",
    short_period: int = 20,
    long_period: int = 50,
) -> pd.Series:
    """Return the sign of short EMA minus long EMA."""
    _validate_periods(short_period, long_period)
    close = pd.to_numeric(df[close_column], errors="coerce")
    short = close.ewm(span=short_period, min_periods=short_period).mean()
    long = close.ewm(span=long_period, min_periods=long_period).mean()
    return pd.Series(np.sign(short - long), index=df.index, name="ema_regime")


def turtle_trader(
    df: pd.DataFrame,
    high_column: str = "High",
    low_column: str = "Low",
    entry_period: int = 50,
    exit_period: int = 20,
) -> pd.Series:
    """Require slower entry and faster trailing regimes to agree."""
    entry = regime_breakout(df, high_column, low_column, entry_period)
    stop = regime_breakout(df, high_column, low_column, exit_period)
    result = np.where(
        entry.eq(1),
        np.where(stop.eq(1), 1, 0),
        np.where(entry.eq(-1), np.where(stop.eq(-1), -1, 0), 0),
    )
    return pd.Series(result, index=df.index, name="turtle_regime")


def composite_regime_score(*signals: pd.Series) -> pd.Series:
    """Sum aligned directional regime signals (-1/0/+1)."""
    if not signals:
        raise ValueError("At least one regime signal is required")
    frame = pd.concat(signals, axis=1)
    return frame.apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1).rename("regime_score")


def regime_fractal(
    df: pd.DataFrame,
    high_column: str = "High",
    low_column: str = "Low",
    window: int = 2,
) -> pd.Series:
    """Return the latest confirmed fractal direction."""
    if window < 1:
        raise ValueError("window must be at least 1")
    highs = pd.to_numeric(df[high_column], errors="coerce")
    lows = pd.to_numeric(df[low_column], errors="coerce")
    width = 2 * window + 1
    high_pivot = highs.eq(highs.rolling(width, center=True, min_periods=width).max())
    low_pivot = lows.eq(lows.rolling(width, center=True, min_periods=width).min())
    confirmed_bear = high_pivot.shift(window, fill_value=False)
    confirmed_bull = low_pivot.shift(window, fill_value=False)
    signal = pd.Series(np.nan, index=df.index, dtype=float, name="fractal_regime")
    signal.loc[confirmed_bear] = -1.0
    signal.loc[confirmed_bull & ~confirmed_bear] = 1.0
    return signal.ffill()


def regime_structure(
    df: pd.DataFrame,
    high_column: str = "High",
    low_column: str = "Low",
    periods: int = 5,
) -> pd.Series:
    """Detect higher-high/higher-low or lower-high/lower-low structure."""
    if periods < 1:
        raise ValueError("periods must be at least 1")
    highs = pd.to_numeric(df[high_column], errors="coerce")
    lows = pd.to_numeric(df[low_column], errors="coerce")
    prior_high = highs.shift(1).rolling(periods, min_periods=periods).max()
    prior_low = lows.shift(1).rolling(periods, min_periods=periods).min()
    higher_high = highs > prior_high
    higher_low = lows > lows.shift(periods)
    lower_low = lows < prior_low
    lower_high = highs < highs.shift(periods)
    return pd.Series(
        np.where(
            higher_high & higher_low,
            1.0,
            np.where(lower_low & lower_high, -1.0, 0.0),
        ),
        index=df.index,
        name="structure_regime",
    )


def regime_floor_ceiling(
    df: pd.DataFrame,
    high_column: str = "High",
    low_column: str = "Low",
    close_column: str = "Close",
    periods: int = 20,
) -> pd.Series:
    """Classify breaks above a prior ceiling or below a prior floor."""
    if periods < 2:
        raise ValueError("periods must be at least 2")
    highs = pd.to_numeric(df[high_column], errors="coerce")
    lows = pd.to_numeric(df[low_column], errors="coerce")
    close = pd.to_numeric(df[close_column], errors="coerce")
    ceiling = highs.shift(1).rolling(periods, min_periods=periods).max()
    floor = lows.shift(1).rolling(periods, min_periods=periods).min()
    return pd.Series(
        np.where(close > ceiling, 1.0, np.where(close < floor, -1.0, 0.0)),
        index=df.index,
        name="floor_ceiling_regime",
    )


def chapter4_regime(
    df: pd.DataFrame | None,
    *,
    breakout_period: int = 20,
    turtle_entry_period: int = 55,
    turtle_exit_period: int = 20,
    ma_short_period: int = 10,
    ma_long_period: int = 30,
    fractal_window: int = 2,
    structure_period: int = 5,
    floor_ceiling_period: int = 20,
    regime_threshold: int = 3,
) -> pd.DataFrame:
    """Combine Chapter 4 methods into one per-bar regime dataframe."""
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "breakout",
                "turtle",
                "sma",
                "ema",
                "fractal",
                "structure",
                "floor_ceiling",
                "regime_score",
                "regime",
            ]
        )

    signals = {
        "breakout": regime_breakout(df, periods=breakout_period),
        "turtle": turtle_trader(
            df,
            entry_period=turtle_entry_period,
            exit_period=turtle_exit_period,
        ),
        "sma": regime_sma(
            df,
            short_period=ma_short_period,
            long_period=ma_long_period,
        ),
        "ema": regime_ema(
            df,
            short_period=ma_short_period,
            long_period=ma_long_period,
        ),
        "fractal": regime_fractal(df, window=fractal_window),
        "structure": regime_structure(df, periods=structure_period),
        "floor_ceiling": regime_floor_ceiling(
            df,
            periods=floor_ceiling_period,
        ),
    }
    result = pd.concat(signals, axis=1)
    result["regime_score"] = composite_regime_score(*signals.values())
    result["regime"] = result["regime_score"].map(
        lambda score: classify_regime(score, threshold=regime_threshold)
    )
    return result


def classify_regime(score: float | int | None, threshold: int = 3) -> str:
    """Map a composite directional score to a descriptive regime bucket."""
    if score is None or pd.isna(score):
        return "INSUFFICIENT DATA"
    threshold = max(1, int(threshold))
    if score >= threshold:
        return "BULLISH"
    if score <= -threshold:
        return "BEARISH"
    return "RANGE / MIXED"


def latest_regime(df: pd.DataFrame | None, **kwargs: Any) -> dict[str, Any]:
    """Return the latest completed-bar Chapter 4 regime snapshot."""
    result = chapter4_regime(df, **kwargs)
    if result.empty:
        return {}
    row = result.iloc[-1]
    return {key: row[key] for key in result.columns}


def multi_timeframe_regime(
    frames: dict[str, pd.DataFrame | None],
    *,
    weights: dict[str, float] | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Summarise the latest regime from the timeframes supplied by the caller."""
    rows: list[dict[str, Any]] = []
    for timeframe, frame in frames.items():
        snapshot = latest_regime(frame, **kwargs)
        if not snapshot:
            continue
        weight = float(weights.get(timeframe, 1.0)) if weights else 1.0
        rows.append(
            {
                "Timeframe": timeframe,
                "Regime": snapshot["regime"],
                "Composite score": snapshot["regime_score"],
                "Weight": weight,
            }
        )

    result = pd.DataFrame(
        rows,
        columns=["Timeframe", "Regime", "Composite score", "Weight"],
    )
    scores = pd.to_numeric(result["Composite score"], errors="coerce")
    valid = scores.notna() & result["Weight"].gt(0)
    result.attrs["weighted_composite_score"] = (
        float(
            (scores[valid] * result.loc[valid, "Weight"]).sum() / result.loc[valid, "Weight"].sum()
        )
        if valid.any()
        else None
    )
    return result


def relative_regime(
    df: pd.DataFrame | None,
    benchmark_close: pd.Series | None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Run the same regime methods on price relative to a benchmark."""
    if df is None or df.empty or benchmark_close is None:
        return pd.DataFrame()
    close = pd.to_numeric(df["Close"], errors="coerce")
    benchmark = pd.to_numeric(benchmark_close, errors="coerce").reindex(df.index)
    relative = close.div(benchmark).replace([np.inf, -np.inf], np.nan)
    synthetic = pd.DataFrame(
        {"High": relative, "Low": relative, "Close": relative},
        index=df.index,
    ).dropna()
    return chapter4_regime(synthetic, **kwargs)


def _validate_periods(short_period: int, long_period: int) -> None:
    if short_period < 2 or long_period < 2:
        raise ValueError("moving-average periods must be at least 2")
    if short_period >= long_period:
        raise ValueError("short_period must be less than long_period")
