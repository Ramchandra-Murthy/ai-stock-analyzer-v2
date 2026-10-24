from __future__ import annotations

import pytest

from modules.fibonacci_gann.backtest import Candle
from modules.fibonacci_gann.signals import generate_daily_fibonacci_gann_signals


def make_candles() -> list[Candle]:
    return [
        Candle("2026-01-01", 100, 105, 95, 100),
        Candle("2026-01-02", 100, 110, 98, 105),
        Candle("2026-01-03", 105, 106, 90, 100),
        Candle("2026-01-04", 100, 104, 99, 100),
        Candle("2026-01-05", 100, 104, 99, 103),
        Candle("2026-01-06", 103, 104, 101, 102),
    ]


def test_signal_requires_full_prior_lookback_and_cross() -> None:
    signals = generate_daily_fibonacci_gann_signals(make_candles(), lookback=4)
    assert signals[:4] == (False, False, False, False)
    assert signals[4] is True
    assert signals[5] is False


def test_lookback_range_excludes_current_bar() -> None:
    candles = make_candles()
    original = generate_daily_fibonacci_gann_signals(candles, lookback=4)
    candles[4] = Candle("2026-01-05", 100, 150, 99, 103)
    changed = generate_daily_fibonacci_gann_signals(candles, lookback=4)
    assert original[4] == changed[4]


def test_returns_all_false_when_history_is_too_short() -> None:
    signals = generate_daily_fibonacci_gann_signals(make_candles()[:3], lookback=4)
    assert signals == (False, False, False)


@pytest.mark.parametrize("lookback", [0, 1, -2, True, 2.5])
def test_rejects_invalid_lookback(lookback: int) -> None:
    with pytest.raises(ValueError, match="lookback"):
        generate_daily_fibonacci_gann_signals(make_candles(), lookback=lookback)


def test_rejects_unordered_timestamps() -> None:
    candles = make_candles()
    candles[3] = Candle("2025-12-31", 100, 104, 99, 100)
    with pytest.raises(ValueError, match="strictly increasing"):
        generate_daily_fibonacci_gann_signals(candles, lookback=4)


def test_rejects_mixed_timezone_conventions_even_when_lookback_is_too_long() -> None:
    candles = make_candles()[:3]
    candles[0] = Candle("2026-01-01T09:15:00+05:30", 100, 105, 95, 100)
    with pytest.raises(ValueError, match="consistent timezone"):
        generate_daily_fibonacci_gann_signals(candles, lookback=20)


def test_rejects_invalid_ohlc_even_when_lookback_is_too_long() -> None:
    candles = make_candles()[:3]
    candles[1] = Candle("2026-01-02", 100, 99, 98, 100)
    with pytest.raises(ValueError, match="high/low"):
        generate_daily_fibonacci_gann_signals(candles, lookback=20)


def test_future_candle_changes_do_not_rewrite_earlier_signals() -> None:
    candles = make_candles()
    original = generate_daily_fibonacci_gann_signals(candles, lookback=4)

    # Change only candles strictly after the point being audited.
    candles[5] = Candle("2026-01-06", 103, 140, 101, 135)
    changed = generate_daily_fibonacci_gann_signals(candles, lookback=4)

    assert changed[:5] == original[:5]


def test_signal_on_last_available_bar_cannot_create_a_trade_without_next_bar() -> None:
    from modules.fibonacci_gann.backtest import BacktestConfig, run_backtest

    candles = make_candles()[:4]
    signals = (False, False, False, True)
    result = run_backtest(candles, signals, BacktestConfig())

    assert result.trades == ()
    assert result.ending_capital == result.starting_capital
