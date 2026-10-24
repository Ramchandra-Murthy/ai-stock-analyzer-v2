from __future__ import annotations

import pytest

from modules.fibonacci_gann.backtest import (
    BacktestConfig,
    Candle,
    run_backtest,
    validate_candles,
)


def candles_for_target() -> list[Candle]:
    return [
        Candle("2026-01-01T09:15", 100, 102, 99, 101),
        Candle("2026-01-01T09:20", 101, 112, 100, 110),
        Candle("2026-01-01T09:25", 110, 111, 109, 110),
    ]


def test_signal_enters_at_next_bar_open_and_target_exit() -> None:
    result = run_backtest(
        candles_for_target(),
        [True, False, False],
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=5),
    )
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_timestamp == "2026-01-01T09:20"
    assert trade.entry_price == 101
    assert trade.exit_price == 111
    assert trade.exit_reason == "target"
    assert trade.quantity == 10
    assert trade.net_pnl == 100
    assert result.win_rate_pct == 100
    assert result.expectancy_per_trade == 100


def test_stop_wins_when_bar_touches_stop_and_target() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        Candle("2026-01-01T09:20", 100, 111, 94, 100),
    ]
    result = run_backtest(
        candles,
        [True, False],
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=5),
    )
    assert result.trades[0].exit_reason == "stop"
    assert result.trades[0].exit_price == 95
    assert result.trades[0].net_pnl == -50


def test_round_trip_costs_and_slippage_reduce_pnl() -> None:
    result = run_backtest(
        candles_for_target(),
        [True, False, False],
        BacktestConfig(
            capital=10_000,
            max_loss_per_trade=50,
            stop_distance=5,
            round_trip_cost_per_unit=0.5,
            slippage_per_unit_per_side=0.25,
        ),
    )
    trade = result.trades[0]
    assert trade.costs == 4
    assert trade.net_pnl < trade.gross_pnl
    assert trade.quantity == 8


def test_no_signals_returns_zero_trade_metrics() -> None:
    result = run_backtest(candles_for_target(), [False, False, False])
    assert result.trades == ()
    assert result.ending_capital == result.starting_capital
    assert result.win_rate_pct == 0
    assert result.expectancy_per_trade == 0
    assert result.profit_factor == 0


def test_rejects_signal_length_mismatch() -> None:
    with pytest.raises(ValueError, match="signals length"):
        run_backtest(candles_for_target(), [True])


def test_rejects_unordered_candles() -> None:
    candles = candles_for_target()
    candles[1] = Candle("2025-12-31T09:20", 101, 112, 100, 110)
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_candles(candles)


def test_rejects_invalid_timestamp_format() -> None:
    candles = candles_for_target()
    candles[1] = Candle("not-a-timestamp", 101, 112, 100, 110)
    with pytest.raises(ValueError, match="valid ISO 8601"):
        validate_candles(candles)


def test_rejects_mixed_timestamp_formats_that_sort_lexically_but_not_chronologically() -> None:
    candles = [
        Candle("2026-1-2", 100, 102, 99, 101),
        Candle("2026-01-10", 101, 112, 100, 110),
    ]
    with pytest.raises(ValueError, match="valid ISO 8601"):
        validate_candles(candles)


def test_rejects_chronologically_unordered_iso_timestamps() -> None:
    candles = [
        Candle("2026-01-10T09:15:00", 100, 102, 99, 101),
        Candle("2026-01-02T09:20:00", 101, 112, 100, 110),
    ]
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_candles(candles)


def test_rejects_mixed_timezone_conventions() -> None:
    candles = [
        Candle("2026-01-01T09:15:00+05:30", 100, 102, 99, 101),
        Candle("2026-01-01T09:20:00", 101, 112, 100, 110),
    ]
    with pytest.raises(ValueError, match="consistent timezone"):
        validate_candles(candles)


def test_rejects_invalid_ohlc() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 99, 98, 100),
        Candle("2026-01-01T09:20", 100, 101, 99, 100),
    ]
    with pytest.raises(ValueError, match="high/low"):
        validate_candles(candles)


def test_rejects_invalid_config() -> None:
    with pytest.raises(ValueError, match="stop_distance"):
        run_backtest(
            candles_for_target(),
            [False, False, False],
            BacktestConfig(stop_distance=0),
        )


def test_position_sizing_uses_remaining_realized_equity() -> None:
    candles = [
        Candle("2026-01-01", 100, 101, 99, 100),
        Candle("2026-01-02", 100, 101, 94, 95),
        Candle("2026-01-03", 100, 101, 99, 100),
        Candle("2026-01-04", 100, 101, 99, 100),
        Candle("2026-01-05", 100, 101, 99, 100),
    ]
    result = run_backtest(
        candles,
        [True, False, True, False, False],
        BacktestConfig(
            capital=1000,
            max_loss_per_trade=500,
            stop_distance=5,
            reward_risk_ratio=2,
        ),
    )

    assert len(result.trades) == 2
    assert result.trades[0].quantity == 10
    assert result.trades[0].net_pnl == -50
    assert result.trades[1].quantity == 9


def test_extreme_exit_slippage_never_creates_negative_fill() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        Candle("2026-01-01T09:20", 100, 101, 99, 100),
    ]
    result = run_backtest(
        candles,
        [True, False],
        BacktestConfig(
            capital=1000,
            max_loss_per_trade=500,
            stop_distance=5,
            slippage_per_unit_per_side=101,
        ),
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_price == 201
    assert trade.exit_price == 0
    assert trade.net_pnl == -402
    assert trade.exit_price >= 0


def test_target_gap_fills_at_open_not_unreachable_target() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        Candle("2026-01-01T09:20", 100, 102, 99, 101),
        Candle("2026-01-01T09:25", 115, 120, 114, 118),
    ]
    result = run_backtest(
        candles,
        [True, False, False],
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=5),
    )

    trade = result.trades[0]
    assert trade.entry_price == 100
    assert trade.exit_price == 115
    assert trade.exit_reason == "target_gap"
    assert trade.net_pnl == 150


def test_intratrade_drawdown_captures_adverse_excursion_before_stop_exit() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        # Both target and stop are touched; the simulator conservatively exits at stop.
        # Intratrade drawdown must still reflect the bar's adverse low after its high.
        Candle("2026-01-01T09:20", 100, 111, 80, 95),
    ]
    result = run_backtest(
        candles,
        [True, False],
        BacktestConfig(capital=1000, max_loss_per_trade=50, stop_distance=5),
    )

    assert result.max_intratrade_drawdown_pct > result.max_drawdown_pct
    assert result.max_intratrade_drawdown_pct > 10


def test_signal_on_exit_bar_can_enter_at_following_bar_open() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        Candle("2026-01-01T09:20", 100, 106, 94, 100),
        Candle("2026-01-01T09:25", 105, 106, 104, 105),
        Candle("2026-01-01T09:30", 105, 106, 104, 105),
    ]
    result = run_backtest(
        candles,
        [True, True, False, False],
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=5),
    )

    assert len(result.trades) == 2
    assert result.trades[0].exit_reason == "stop"
    assert result.trades[0].exit_timestamp == "2026-01-01T09:20"
    assert result.trades[1].entry_timestamp == "2026-01-01T09:25"
    assert result.trades[1].entry_price == 105


def test_signal_after_unsized_entry_is_preserved() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        # The first signal cannot afford one share at this open.
        Candle("2026-01-01T09:20", 200, 201, 199, 200),
        Candle("2026-01-01T09:25", 50, 51, 49, 50),
        Candle("2026-01-01T09:30", 50, 51, 49, 50),
    ]
    result = run_backtest(
        candles,
        [True, True, False, False],
        BacktestConfig(
            capital=100,
            max_loss_per_trade=50,
            stop_distance=5,
        ),
    )

    assert len(result.trades) == 1
    assert result.trades[0].entry_timestamp == "2026-01-01T09:25"
    assert result.trades[0].entry_price == 50


def test_gap_exit_drawdown_ignores_prices_after_open_exit() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        Candle("2026-01-01T09:20", 100, 101, 99, 100),
        # The stop is gapped through at 90; the later low of 50 is post-exit.
        Candle("2026-01-01T09:25", 90, 95, 50, 60),
    ]
    result = run_backtest(
        candles,
        [True, False, False],
        BacktestConfig(capital=1000, max_loss_per_trade=50, stop_distance=5),
    )

    assert result.trades[0].exit_reason == "stop_gap"
    assert result.trades[0].exit_price == 90
    assert result.max_intratrade_drawdown_pct < 15


def test_gap_drawdown_uses_non_negative_exit_fill_under_extreme_slippage() -> None:
    candles = [
        Candle("2026-01-01T09:15", 100, 101, 99, 100),
        Candle("2026-01-01T09:20", 100, 101, 99, 100),
        Candle("2026-01-01T09:25", 50, 55, 40, 45),
    ]
    result = run_backtest(
        candles,
        [True, False, False],
        BacktestConfig(
            capital=1000,
            max_loss_per_trade=500,
            stop_distance=5,
            slippage_per_unit_per_side=101,
        ),
    )

    trade = result.trades[0]
    assert trade.exit_reason == "stop_gap"
    assert trade.exit_price == 0
    # The drawdown mark must match the clamped fill used by the trade ledger.
    assert result.max_intratrade_drawdown_pct == pytest.approx(40.2)
