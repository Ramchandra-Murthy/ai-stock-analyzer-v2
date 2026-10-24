from __future__ import annotations

import pandas as pd


def regime_breakdown(
    df: pd.DataFrame,
    high_lookback: int = 50,
    low_lookback: int = 50,
) -> pd.Series:
    """Classify each bar from fresh highs/lows over prior rolling windows.

    A fresh high is classified as bullish, a fresh low as bearish, and all
    other observations as neutral. The current bar is compared with prior
    observations only, avoiding look-ahead from the current bar.
    """
    if high_lookback < 1 or low_lookback < 1:
        raise ValueError("lookback windows must be positive")

    required = {"High", "Low"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    highs = pd.to_numeric(df["High"], errors="coerce")
    lows = pd.to_numeric(df["Low"], errors="coerce")

    prior_high = highs.shift(1).rolling(high_lookback, min_periods=high_lookback).max()
    prior_low = lows.shift(1).rolling(low_lookback, min_periods=low_lookback).min()

    regime = pd.Series("NEUTRAL", index=df.index, dtype="string")
    regime.loc[highs > prior_high] = "BULLISH"
    regime.loc[lows < prior_low] = "BEARISH"

    return regime


def higher_highs_lows(
    df: pd.DataFrame,
    levels: int = 3,
    shift: int = 2,
) -> pd.DataFrame:
    """Classify higher/lower fractal swings and their regime reference.

    Chapter 4 builds this method from fractal swing highs and lows. A
    bullish pattern requires a higher high and higher low; a bearish pattern
    requires a lower low and lower high. The default shift of two swings uses
    the penultimate swing as the regime reference, giving the definition some
    wiggle room against noise.
    """
    if levels < 1:
        raise ValueError("levels must be positive")
    if shift < 1:
        raise ValueError("shift must be positive")
    required = {"High", "Low", "Close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    result = df.copy()
    swings = fractal_swings(df, levels=levels)

    for level in range(1, levels + 1):
        hi_col = f"Hi{level}"
        lo_col = f"Lo{level}"
        if hi_col not in swings.columns or lo_col not in swings.columns:
            break

        highs = pd.to_numeric(swings[hi_col], errors="coerce")
        lows = pd.to_numeric(swings[lo_col], errors="coerce")
        previous_high = highs.ffill().shift(1)
        previous_low = lows.ffill().shift(1)

        hh = highs.where(highs.notna() & (highs > previous_high))
        lh = highs.where(highs.notna() & (highs < previous_high))
        hl = lows.where(lows.notna() & (lows > previous_low))
        ll = lows.where(lows.notna() & (lows < previous_low))

        result[f"HH{level}"] = hh
        result[f"HL{level}"] = hl
        result[f"LH{level}"] = lh
        result[f"LL{level}"] = ll

        bullish_reference = hl.shift(shift).ffill()
        bearish_reference = lh.shift(shift).ffill()
        close = pd.to_numeric(df["Close"], errors="coerce")
        bullish = hh.notna() & bullish_reference.notna() & (close > bullish_reference)
        bearish = ll.notna() & bearish_reference.notna() & (close < bearish_reference)

        regime = pd.Series("NEUTRAL", index=df.index, dtype="string")
        regime.loc[bullish] = "BULLISH"
        regime.loc[bearish] = "BEARISH"
        result[f"HiLo_HH{level}"] = regime

    return result


def floor_ceiling_regime(
    df: pd.DataFrame,
    levels: int = 3,
) -> pd.DataFrame:
    """Classify a two-state regime from fractal floors and ceilings.

    Chapter 4 describes floor and ceiling as a variation of higher
    highs/higher lows. A higher swing low establishes a floor and a lower
    swing high establishes a ceiling. In the conservative form, a bearish
    regime turns bullish when price crosses the ceiling; a bullish regime
    turns bearish when price crosses the floor. Sideways movement is therefore
    treated as a pause inside the current bull/bear context.
    """
    if levels < 1:
        raise ValueError("levels must be positive")
    required = {"High", "Low", "Close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    result = df.copy()
    swings = fractal_swings(df, levels=levels)
    close = pd.to_numeric(df["Close"], errors="coerce")

    for level in range(1, levels + 1):
        hi_col = f"Hi{level}"
        lo_col = f"Lo{level}"
        if hi_col not in swings.columns or lo_col not in swings.columns:
            break

        highs = pd.to_numeric(swings[hi_col], errors="coerce")
        lows = pd.to_numeric(swings[lo_col], errors="coerce")
        previous_high = highs.ffill().shift(1)
        previous_low = lows.ffill().shift(1)

        floor = lows.where(lows.notna() & (lows > previous_low)).ffill()
        ceiling = highs.where(highs.notna() & (highs < previous_high)).ffill()

        regime = pd.Series("NEUTRAL", index=df.index, dtype="string")
        state = "NEUTRAL"
        for idx in df.index:
            price = close.loc[idx]
            floor_value = floor.loc[idx]
            ceiling_value = ceiling.loc[idx]
            if pd.isna(price):
                regime.loc[idx] = state
                continue
            if state == "BEARISH" and pd.notna(ceiling_value) and price > ceiling_value:
                state = "BULLISH"
            elif state == "BULLISH" and pd.notna(floor_value) and price < floor_value:
                state = "BEARISH"
            elif state == "NEUTRAL":
                if pd.notna(ceiling_value) and price > ceiling_value:
                    state = "BULLISH"
                elif pd.notna(floor_value) and price < floor_value:
                    state = "BEARISH"
            regime.loc[idx] = state

        result[f"Floor{level}"] = floor
        result[f"Ceiling{level}"] = ceiling
        result[f"HiLo_FC{level}"] = regime

    return result


def turtle_regime(
    df: pd.DataFrame,
    entry_lookback: int = 50,
    exit_lookback: int = 20,
) -> pd.Series:
    """Classify a simplified Turtle regime using asymmetric breakouts.

    The longer entry window establishes direction. The shorter exit window
    acts as the faster confirmation/stop regime. A signal is emitted only
    when both regimes agree; disagreement is neutral. This mirrors the
    Chapter 4 simplified Turtle construction while keeping the implementation
    free of look-ahead by delegating to :func:`regime_breakdown`.
    """
    if entry_lookback < 1 or exit_lookback < 1:
        raise ValueError("lookback windows must be positive")

    entry_regime = regime_breakdown(
        df,
        high_lookback=entry_lookback,
        low_lookback=entry_lookback,
    )
    exit_regime = regime_breakdown(
        df,
        high_lookback=exit_lookback,
        low_lookback=exit_lookback,
    )

    turtle = pd.Series("NEUTRAL", index=df.index, dtype="string")
    bullish = (entry_regime == "BULLISH") & (exit_regime == "BULLISH")
    bearish = (entry_regime == "BEARISH") & (exit_regime == "BEARISH")
    turtle.loc[bullish] = "BULLISH"
    turtle.loc[bearish] = "BEARISH"
    return turtle


def moving_average_regime(
    df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    price_column: str = "Close",
) -> pd.Series:
    """Classify regime from a fast/slow moving-average crossover.

    A fast moving average above the slow moving average is bullish, below it
    is bearish, and equality is neutral. Rolling windows use only observations
    available at each bar, so the regime does not introduce look-ahead.
    """
    if fast_window < 1 or slow_window < 1:
        raise ValueError("moving-average windows must be positive")
    if fast_window >= slow_window:
        raise ValueError("fast_window must be smaller than slow_window")
    if price_column not in df.columns:
        raise ValueError(f"missing required column: {price_column}")

    prices = pd.to_numeric(df[price_column], errors="coerce")
    fast_ma = prices.rolling(fast_window, min_periods=fast_window).mean()
    slow_ma = prices.rolling(slow_window, min_periods=slow_window).mean()

    regime = pd.Series("NEUTRAL", index=df.index, dtype="string")
    regime.loc[fast_ma > slow_ma] = "BULLISH"
    regime.loc[fast_ma < slow_ma] = "BEARISH"
    return regime


def fractal_swings(
    df: pd.DataFrame,
    levels: int = 3,
) -> pd.DataFrame:
    """Calculate recursive fractal swing highs and lows.

    The Chapter 4 construction uses the average of High, Low, and Close as
    the source series. Level 1 identifies local swings from adjacent bars;
    each higher level identifies swings from the preceding level's swings.
    The returned columns are sparse swing-price series indexed like the input.
    """
    if levels < 1:
        raise ValueError("levels must be positive")
    required = {"High", "Low", "Close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    source = df[["High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    result = pd.DataFrame(index=df.index)

    current = source.dropna()
    for level in range(1, levels + 1):
        if len(current) < 3:
            break

        previous = current.shift(1)
        following = current.shift(-1)
        lows = current[(current <= previous) & (current < following)]
        highs = current[(current >= previous) & (current > following)]

        result[f"Lo{level}"] = lows.reindex(df.index)
        result[f"Hi{level}"] = highs.reindex(df.index)

        swings = pd.concat([lows.rename("value"), highs.rename("value")]).sort_index()
        swings = swings[~swings.index.duplicated(keep="first")]
        current = swings

    return result
