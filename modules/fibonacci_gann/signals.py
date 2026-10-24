"""Causal daily Fibonacci/Gann-style research signals.

This is a transparent, rules-based educational hypothesis, not a validated edge:
at each bar close, use the preceding N bars to form a price range, compute the
range's Fibonacci retracement levels and Gann eighths, and signal when price
crosses upward through the 5/8 Gann level while the prior close was inside the
38.2%-61.8% Fibonacci retracement zone. The current bar is excluded from the
range. Backtests must enter no earlier than the following bar's open.
"""

from __future__ import annotations

from collections.abc import Sequence

from modules.fibonacci_gann.backtest import Candle, validate_candles


def generate_daily_fibonacci_gann_signals(
    candles: Sequence[Candle],
    *,
    lookback: int = 20,
) -> tuple[bool, ...]:
    """Generate causal long-entry research signals from daily OHLC candles.

    A signal is emitted at bar i close only when:
    - a full lookback range exists using bars i-lookback through i-1;
    - bar i-1 close lies between the prior range's 38.2% and 61.8%
      Fibonacci retracement prices (inclusive); and
    - bar i close crosses upward through the prior range's 5/8 Gann level.

    All levels are based solely on bars preceding i. This is a heuristic rule,
    not a claim that Fibonacci/Gann levels predict future prices.
    """
    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 2:
        raise ValueError("lookback must be an integer of at least 2")

    validate_candles(candles)
    count = len(candles)
    signals = [False] * count
    if count <= lookback:
        return tuple(signals)

    for index in range(lookback, count):
        prior = candles[index - lookback : index]
        swing_low = min(bar.low for bar in prior)
        swing_high = max(bar.high for bar in prior)
        price_range = swing_high - swing_low
        if price_range <= 0:
            continue

        # Fibonacci retracement prices for an upward range: H - ratio * range.
        fib_382 = swing_high - 0.382 * price_range
        fib_618 = swing_high - 0.618 * price_range
        pullback_low, pullback_high = sorted((fib_382, fib_618))

        # Gann 5/8 level from the same prior range; never uses the current bar.
        gann_5_8 = swing_low + 5 * price_range / 8
        previous_close = candles[index - 1].close
        current_close = candles[index].close
        in_fib_pullback = pullback_low <= previous_close <= pullback_high
        crossed_up_gann = previous_close <= gann_5_8 < current_close
        signals[index] = in_fib_pullback and crossed_up_gann

    return tuple(signals)
