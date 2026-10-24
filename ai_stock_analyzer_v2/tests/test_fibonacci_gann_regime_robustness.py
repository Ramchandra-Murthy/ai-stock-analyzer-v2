from __future__ import annotations

import pytest

from modules.fibonacci_gann.backtest import BacktestConfig, Candle
from modules.fibonacci_gann.regime_robustness import evaluate_regime_robustness


def sample_candles() -> list[Candle]:
    closes = [100, 101, 102, 103, 102, 101, 100, 99]
    return [
        Candle(f"2026-01-01T09:{15 + index * 5:02d}", close, close + 2, close - 2, close)
        for index, close in enumerate(closes)
    ]


def test_evaluates_caller_labelled_non_overlapping_regimes() -> None:
    results = evaluate_regime_robustness(
        sample_candles(),
        [True, False, True, False, True, False, True, False],
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=1),
        regimes={"trending": (0, 4), "sideways": (4, 8)},
    )
    assert [item.regime for item in results] == ["trending", "sideways"]
    assert [item.candle_count for item in results] == [4, 4]
    assert all(item.result.starting_capital == 10_000 for item in results)


def test_rejects_empty_regime_mapping() -> None:
    with pytest.raises(ValueError, match="at least one regime"):
        evaluate_regime_robustness(sample_candles(), [False] * 8, BacktestConfig(), regimes={})


def test_rejects_overlapping_windows() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        evaluate_regime_robustness(
            sample_candles(),
            [False] * 8,
            BacktestConfig(),
            regimes={"trending": (0, 5), "volatile": (4, 8)},
        )


def test_rejects_too_short_or_out_of_range_windows() -> None:
    with pytest.raises(ValueError, match="at least two"):
        evaluate_regime_robustness(
            sample_candles(), [False] * 8, BacktestConfig(), regimes={"short": (2, 3)}
        )
    with pytest.raises(ValueError, match="at least two"):
        evaluate_regime_robustness(
            sample_candles(), [False] * 8, BacktestConfig(), regimes={"outside": (7, 10)}
        )


def test_rejects_signal_length_mismatch_and_non_boolean_signals() -> None:
    with pytest.raises(ValueError, match="signals length"):
        evaluate_regime_robustness(
            sample_candles(), [False], BacktestConfig(), regimes={"sample": (0, 2)}
        )
    with pytest.raises(ValueError, match="only booleans"):
        evaluate_regime_robustness(
            sample_candles(), [0] * 8, BacktestConfig(), regimes={"sample": (0, 2)}
        )
