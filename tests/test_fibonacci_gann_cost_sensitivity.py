from __future__ import annotations

import pytest

from modules.fibonacci_gann.backtest import BacktestConfig, Candle
from modules.fibonacci_gann.cost_sensitivity import evaluate_cost_sensitivity


def sample_candles() -> list[Candle]:
    return [
        Candle("2026-01-01T09:15", 100, 102, 99, 101),
        Candle("2026-01-01T09:20", 101, 112, 100, 110),
        Candle("2026-01-01T09:25", 110, 111, 109, 110),
    ]


def test_cost_sensitivity_runs_all_cost_and_slippage_combinations() -> None:
    rows = evaluate_cost_sensitivity(
        sample_candles(),
        [True, False, False],
        BacktestConfig(capital=10_000, max_loss_per_trade=50, stop_distance=5),
        round_trip_costs=[0, 0.5],
        slippage_per_side_values=[0, 0.25],
    )
    assert len(rows) == 4
    assert [(row.round_trip_cost_per_unit, row.slippage_per_unit_per_side) for row in rows] == [
        (0.0, 0.0),
        (0.0, 0.25),
        (0.5, 0.0),
        (0.5, 0.25),
    ]
    baseline = rows[0].result
    higher_cost = rows[-1].result
    assert higher_cost.ending_capital < baseline.ending_capital


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"round_trip_costs": []}, "round_trip_costs must not be empty"),
        ({"slippage_per_side_values": []}, "slippage_per_side_values must not be empty"),
        ({"round_trip_costs": [-0.1]}, "round_trip_costs values must be finite and non-negative"),
        (
            {"slippage_per_side_values": [float("nan")]},
            "slippage_per_side_values values must be finite and non-negative",
        ),
    ],
)
def test_rejects_invalid_sensitivity_values(kwargs: dict, message: str) -> None:
    args = {
        "round_trip_costs": [0],
        "slippage_per_side_values": [0],
        **kwargs,
    }
    with pytest.raises(ValueError, match=message):
        evaluate_cost_sensitivity(
            sample_candles(),
            [False, False, False],
            BacktestConfig(),
            **args,
        )
