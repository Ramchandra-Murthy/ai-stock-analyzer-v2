"""Tests for chronological walk-forward validation."""

import pytest

from modules.fibonacci_gann.backtest import BacktestConfig, Candle
from modules.fibonacci_gann.walk_forward import evaluate_walk_forward


@pytest.fixture
def candles():
    return tuple(
        Candle(f"2026-01-{day:02d}", 100 + day, 102 + day, 99 + day, 101 + day)
        for day in range(1, 11)
    )


def test_walk_forward_folds_are_chronological_and_disjoint(candles):
    seen = []

    def signal(history, config):
        seen.append(history[-1].timestamp)
        return len(history) >= 2 and history[-1].close > history[-2].close

    folds = evaluate_walk_forward(
        candles, signal, BacktestConfig(), initial_train_size=4, test_size=3
    )

    assert [(fold.test_start, fold.test_end) for fold in folds] == [
        ("2026-01-05", "2026-01-07"),
        ("2026-01-08", "2026-01-10"),
    ]
    assert all(fold.train_end < fold.test_start for fold in folds)
    assert all(fold.test_candle_count == 3 for fold in folds)
    assert seen == [
        candles[3].timestamp,
        *(candle.timestamp for candle in candles[4:7]),
        candles[6].timestamp,
        *(candle.timestamp for candle in candles[7:]),
    ]


def test_signal_callback_never_receives_future_candles(candles):
    def signal(history, config):
        assert history[-1].timestamp <= candles[-1].timestamp
        assert all(
            history[index].timestamp < history[index + 1].timestamp
            for index in range(len(history) - 1)
        )
        return False

    folds = evaluate_walk_forward(
        candles, signal, BacktestConfig(), initial_train_size=4, test_size=3
    )
    assert len(folds) == 2
    assert all(not fold.result.trades for fold in folds)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"initial_train_size": 0, "test_size": 3}, "initial_train_size"),
        ({"initial_train_size": 4, "test_size": 1}, "test_size"),
        ({"initial_train_size": 4, "test_size": 3, "step_size": 0}, "step_size"),
        ({"initial_train_size": 4, "test_size": 3, "step_size": 2}, "prevent overlapping"),
    ],
)
def test_rejects_invalid_window_sizes(candles, kwargs, message):
    with pytest.raises(ValueError, match=message):
        evaluate_walk_forward(candles, lambda history, config: False, BacktestConfig(), **kwargs)


def test_rejects_non_boolean_signals(candles):
    with pytest.raises(ValueError, match="must return a bool"):
        evaluate_walk_forward(
            candles,
            lambda history, config: 1,
            BacktestConfig(),
            initial_train_size=4,
            test_size=3,
        )


def test_walk_forward_includes_short_final_fold_with_two_candles(candles):
    extended_candles = candles + (
        Candle("2026-01-11", 111, 113, 110, 112),
        Candle("2026-01-12", 112, 114, 111, 113),
    )

    folds = evaluate_walk_forward(
        extended_candles,
        lambda history, config: False,
        BacktestConfig(),
        initial_train_size=4,
        test_size=3,
    )

    assert [fold.test_candle_count for fold in folds] == [3, 3, 2]
    assert folds[-1].test_start == "2026-01-11"
    assert folds[-1].test_end == "2026-01-12"
    assert all(fold.result.trades == () for fold in folds)


def test_signal_on_last_training_candle_can_enter_at_first_test_open():
    candles = (
        Candle("2026-01-01", 100, 101, 99, 100),
        Candle("2026-01-02", 101, 102, 100, 101),
        Candle("2026-01-03", 102, 103, 101, 102),
        Candle("2026-01-04", 105, 116, 104, 115),
        Candle("2026-01-05", 115, 116, 114, 115),
    )

    folds = evaluate_walk_forward(
        candles,
        lambda history, config: history[-1].timestamp == "2026-01-03",
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=5),
        initial_train_size=3,
        test_size=2,
    )

    assert len(folds) == 1
    assert folds[0].test_start == "2026-01-04"
    assert len(folds[0].result.trades) == 1
    assert folds[0].result.trades[0].entry_timestamp == "2026-01-04"
    assert folds[0].result.trades[0].entry_price == 105
