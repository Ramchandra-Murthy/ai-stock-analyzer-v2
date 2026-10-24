"""Tests for the isolated, leakage-resistant Fibonacci/Gann validation harness."""

import pytest

from modules.fibonacci_gann.backtest import BacktestConfig, Candle
from modules.fibonacci_gann.validation import (
    ValidationCase,
    build_causal_signals,
    evaluate_parameter_sensitivity,
)


@pytest.fixture
def fixed_candles() -> tuple[Candle, ...]:
    """Small deterministic OHLC sample; deliberately not downloaded market data."""
    return (
        Candle("2026-01-01", 100, 102, 99, 101),
        Candle("2026-01-02", 101, 104, 100, 103),
        Candle("2026-01-03", 103, 105, 101, 102),
        Candle("2026-01-04", 102, 106, 101, 105),
        Candle("2026-01-05", 105, 107, 103, 106),
        Candle("2026-01-06", 106, 108, 104, 107),
    )


def test_signal_callback_only_receives_history_prefixes(fixed_candles):
    seen_lengths = []

    def signal(history, config):
        seen_lengths.append(len(history))
        assert history[-1].timestamp == fixed_candles[len(history) - 1].timestamp
        assert len(history) <= len(fixed_candles)
        return len(history) >= 2 and history[-1].close > history[-2].close

    signals = build_causal_signals(fixed_candles, signal, BacktestConfig())

    assert seen_lengths == list(range(1, len(fixed_candles) + 1))
    assert len(signals) == len(fixed_candles)
    assert signals[0] is False
    assert signals[1] is True


def test_parameter_sensitivity_returns_one_result_per_case(fixed_candles):
    def signal(history, config):
        return len(history) >= 2 and history[-1].close > history[-2].close

    cases = (
        ValidationCase("tight-stop", BacktestConfig(stop_distance=2, reward_risk_ratio=1.5)),
        ValidationCase("wide-stop", BacktestConfig(stop_distance=4, reward_risk_ratio=2)),
    )
    outcomes = evaluate_parameter_sensitivity(fixed_candles, cases, signal)

    assert [item.name for item in outcomes] == ["tight-stop", "wide-stop"]
    assert all(item.result.starting_capital == 10_000 for item in outcomes)
    assert all(item.result.ending_capital >= 0 for item in outcomes)


def test_rejects_empty_or_duplicate_case_names(fixed_candles):
    def signal(history, config):
        return False

    config = BacktestConfig()

    with pytest.raises(ValueError, match="non-empty"):
        evaluate_parameter_sensitivity(fixed_candles, (ValidationCase(" ", config),), signal)
    with pytest.raises(ValueError, match="unique"):
        evaluate_parameter_sensitivity(
            fixed_candles,
            (ValidationCase("same", config), ValidationCase("same", config)),
            signal,
        )


def test_rejects_risk_ceiling_above_capital(fixed_candles):
    case = ValidationCase("invalid-risk", BacktestConfig(capital=100, max_loss_per_trade=101))
    with pytest.raises(ValueError, match="cannot exceed"):
        evaluate_parameter_sensitivity(fixed_candles, (case,), lambda history, config: False)


def test_rejects_non_boolean_signal(fixed_candles):
    with pytest.raises(ValueError, match="must return a bool"):
        build_causal_signals(
            fixed_candles,
            lambda history, config: 1,
            BacktestConfig(),
        )
