from __future__ import annotations

import pytest

from modules.fibonacci_gann.backtest import BacktestConfig, Candle
from modules.fibonacci_gann.parameter_sensitivity import evaluate_parameter_sensitivity


def sample_candles() -> list[Candle]:
    closes = [100, 101, 102, 103, 102, 104, 105, 103]
    return [
        Candle(f"2026-01-01T09:{15 + index * 5:02d}", close, close + 2, close - 2, close)
        for index, close in enumerate(closes)
    ]


def test_compares_named_parameter_variants_independently() -> None:
    variants = {
        "baseline": BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=1),
        "wider_stop": BacktestConfig(
            capital=10_000, max_loss_per_trade=50, stop_distance=2, reward_risk_ratio=2
        ),
    }
    results = evaluate_parameter_sensitivity(
        sample_candles(), [True, False, True, False, True, False, True, False], variants
    )
    assert [item.variant for item in results] == ["baseline", "wider_stop"]
    assert all(item.result.starting_capital == 10_000 for item in results)
    assert all(item.config == variants[item.variant] for item in results)


def test_rejects_empty_variants() -> None:
    with pytest.raises(ValueError, match="at least one"):
        evaluate_parameter_sensitivity(sample_candles(), [False] * 8, {})


def test_rejects_signal_length_mismatch() -> None:
    with pytest.raises(ValueError, match="signals length"):
        evaluate_parameter_sensitivity(sample_candles(), [False], {"baseline": BacktestConfig()})


def test_rejects_non_boolean_signals() -> None:
    with pytest.raises(ValueError, match="only booleans"):
        evaluate_parameter_sensitivity(sample_candles(), [0] * 8, {"baseline": BacktestConfig()})


def test_rejects_invalid_variant_values() -> None:
    with pytest.raises(ValueError, match="must use a BacktestConfig"):
        evaluate_parameter_sensitivity(
            sample_candles(), [False] * 8, {"bad": "not a config"}  # type: ignore[dict-item]
        )


def test_builds_all_twelve_lookback_reward_risk_combinations() -> None:
    from modules.fibonacci_gann.parameter_sensitivity import build_parameter_grid

    base = BacktestConfig(
        capital=5000,
        max_loss_per_trade=250,
        stop_distance=4,
        reward_risk_ratio=1.5,
        round_trip_cost_per_unit=0.2,
        slippage_per_unit_per_side=0.1,
    )
    cases = build_parameter_grid(base)

    assert len(cases) == 12
    assert [(case.lookback, case.reward_risk_ratio) for case in cases] == [
        (lookback, ratio) for lookback in (10, 20, 30, 50) for ratio in (2.0, 2.5, 3.0)
    ]
    assert all(case.config.capital == 5000 for case in cases)
    assert all(case.config.stop_distance == 4 for case in cases)
    assert all(case.config.round_trip_cost_per_unit == 0.2 for case in cases)
    assert all(case.config.slippage_per_unit_per_side == 0.1 for case in cases)


def test_parameter_grid_rejects_invalid_values() -> None:
    from modules.fibonacci_gann.parameter_sensitivity import build_parameter_grid

    with pytest.raises(ValueError, match="positive integers"):
        build_parameter_grid(BacktestConfig(), lookbacks=(10, 0))
    with pytest.raises(ValueError, match="greater than zero"):
        build_parameter_grid(BacktestConfig(), reward_risk_ratios=(2.0, float("nan")))
