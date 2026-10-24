"""Tests for the leakage-safe AI walk-forward backtester."""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import ai_trading.walk_forward as walk_forward_module
from ai_trading.walk_forward import walk_forward_backtest


def _market_frame(rows: int = 240) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    returns = rng.normal(0.0008, 0.015, rows)
    close = 100.0 * np.exp(np.cumsum(returns))
    open_prices = close * (1.0 + rng.normal(0.0, 0.002, rows))
    return pd.DataFrame(
        {
            "Open": open_prices,
            "Close": close,
            "Volume": rng.integers(900_000, 1_100_000, rows),
        }
    )


def test_walk_forward_backtest_has_non_overlapping_trades() -> None:
    trades, result = walk_forward_backtest(
        _market_frame(),
        horizon=5,
        threshold=0.0,
        initial_train=100,
    )
    assert not trades.empty
    assert result.trades >= 0
    assert result.final_equity > 0.0
    assert result.max_drawdown <= 0.0
    assert 0.0 <= result.win_rate <= 1.0

    entries = pd.to_datetime(trades["entry_index"])
    exits = pd.to_datetime(trades["exit_index"])
    if len(entries) > 1:
        assert all(entries.iloc[i] >= exits.iloc[i - 1] for i in range(1, len(entries)))


def test_backtest_respects_transaction_costs() -> None:
    frame = _market_frame()
    _, free_result = walk_forward_backtest(
        frame,
        horizon=5,
        threshold=0.0,
        initial_train=100,
        transaction_cost_bps=0.0,
    )
    _, costly_result = walk_forward_backtest(
        frame,
        horizon=5,
        threshold=0.0,
        initial_train=100,
        transaction_cost_bps=20.0,
    )
    assert costly_result.final_equity <= free_result.final_equity


@pytest.mark.parametrize("cost_bps", [float("nan"), float("inf"), float("-inf")])
def test_backtest_rejects_non_finite_transaction_costs(cost_bps: float) -> None:
    with pytest.raises(ValueError, match="transaction_cost_bps must be finite"):
        walk_forward_backtest(
            _market_frame(),
            horizon=5,
            threshold=0.0,
            initial_train=100,
            transaction_cost_bps=cost_bps,
        )


def test_prediction_uses_next_bar_open_for_execution_without_training_leakage() -> None:
    frame = _market_frame()
    training_lengths: list[int] = []
    refit_flags: list[bool] = []
    prediction_frames: list[pd.DataFrame] = []

    def fake_train_model(
        train_frame: pd.DataFrame,
        *,
        horizon: int,
        threshold: float,
        test_fraction: float,
        refit_full: bool,
    ) -> tuple[object, None]:
        training_lengths.append(len(train_frame))
        refit_flags.append(refit_full)
        return object(), None

    def fake_predict_latest(
        model: object, prediction_frame: pd.DataFrame
    ) -> dict[str, float | str]:
        prediction_frames.append(prediction_frame.copy())
        return {"probability_up": 0.6, "confidence": 0.2, "signal": "LONG"}

    with (
        patch.object(walk_forward_module, "train_model", side_effect=fake_train_model),
        patch.object(
            walk_forward_module,
            "predict_latest",
            side_effect=fake_predict_latest,
        ),
    ):
        trades, _ = walk_forward_backtest(
            frame,
            horizon=5,
            threshold=0.0,
            initial_train=100,
        )

    assert training_lengths
    assert prediction_frames
    assert refit_flags and all(refit_flags)
    assert training_lengths[0] == 100
    assert len(prediction_frames[0]) == 101
    assert prediction_frames[0].index[-1] == frame.index[100]
    assert prediction_frames[0].index[-1] not in frame.iloc[:100].index
    first_trade = trades.iloc[0]
    assert first_trade["decision_index"] == frame.index[100]
    assert first_trade["entry_index"] == frame.index[101]
    assert first_trade["entry_price"] == frame["Open"].iloc[101]
    assert first_trade["exit_index"] == frame.index[105]
    assert first_trade["exit_price"] == frame["Close"].iloc[105]


def test_close_only_backtest_delays_entry_until_next_bar() -> None:
    frame = _market_frame().drop(columns=["Open"])
    trades, _ = walk_forward_backtest(
        frame,
        horizon=5,
        threshold=0.0,
        initial_train=100,
    )
    first_trade = trades.iloc[0]
    assert first_trade["decision_index"] == frame.index[100]
    assert first_trade["entry_index"] == frame.index[101]
    assert first_trade["entry_price"] == frame["Close"].iloc[101]
    assert first_trade["exit_index"] == frame.index[106]


def test_backtest_rejects_infinite_execution_prices() -> None:
    frame = _market_frame()
    frame.loc[:, "Open"] = float("inf")
    frame.loc[:, "Close"] = float("inf")

    with (
        patch.object(walk_forward_module, "train_model", return_value=(object(), None)),
        patch.object(
            walk_forward_module,
            "predict_latest",
            return_value={"probability_up": 0.6, "confidence": 0.2, "signal": "LONG"},
        ),
    ):
        with pytest.raises(ValueError, match="no valid walk-forward trades"):
            walk_forward_backtest(
                frame,
                horizon=5,
                threshold=0.0,
                initial_train=100,
            )
