"""Trade-return accounting includes closing costs and directional reversals."""

import numpy as np
import pandas as pd
import pytest

from algorithmic_trading.backtester import _trade_returns


def _reference(data: pd.DataFrame) -> pd.Series:
    """Small loop oracle for directional trade grouping and closing-cost allocation."""
    results = []
    equity = None
    previous = 0.0
    costs = data.get("transaction_cost", pd.Series(0.0, index=data.index))
    for position, strategy_return, transaction_cost in zip(
        data["position"], data["strategy_return"], costs, strict=True
    ):
        current = float(position)
        cost = float(transaction_cost) if pd.notna(transaction_cost) else 0.0
        bar_return = float(strategy_return) if pd.notna(strategy_return) else 0.0

        if previous == 0.0 and current != 0.0:
            equity = 1.0 + bar_return
        elif previous != 0.0 and current == 0.0:
            equity *= 1.0 - cost
            results.append(equity - 1.0)
            equity = None
        elif previous != 0.0 and current != 0.0 and np.sign(previous) != np.sign(current):
            closing_cost = cost * abs(previous) / abs(current - previous)
            equity *= 1.0 - closing_cost
            results.append(equity - 1.0)
            equity = 1.0 + bar_return + closing_cost
        elif current != 0.0:
            equity *= 1.0 + bar_return

        previous = current

    if equity is not None:
        results.append(equity - 1.0)
    result = pd.Series(results, index=range(1, len(results) + 1), dtype=float)
    result.index.name = "position"
    return result


def _frame(position, returns, transaction_cost=None) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-01", periods=len(position))
    costs = (
        np.zeros(len(position)) if transaction_cost is None else np.asarray(transaction_cost, float)
    )
    return pd.DataFrame(
        {
            "position": np.asarray(position, float),
            "strategy_return": np.asarray(returns, float),
            "transaction_cost": costs,
        },
        index=index,
    )


@pytest.mark.parametrize("seed", range(40))
def test_matches_reference_on_random_positions(seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = int(rng.integers(2, 600))
    position = rng.choice([-1.0, 0.0, 0.5, 1.0], size=n, p=[0.2, 0.3, 0.1, 0.4])
    returns = rng.normal(0.0005, 0.02, n)
    data = _frame(position, returns)

    pd.testing.assert_series_equal(_trade_returns(data), _reference(data), rtol=0, atol=1e-15)


@pytest.mark.parametrize(
    "position, returns",
    [
        ([0, 0, 0, 0], [0.01, -0.02, 0.03, 0.0]),  # never in the market
        ([1, 1, 1, 1], [0.01, -0.02, 0.03, 0.0]),  # one long trade
        ([1, -1, 1, -1], [0.01, -0.02, 0.03, 0.04]),  # flips count as new trades
        ([1, 0, 1, 0, 1], [0.01, 0.02, 0.03, 0.02, -0.5]),  # separate trades
        ([1, 1, 1], [0.0, np.nan, 0.02]),  # NaN inside a trade is skipped like before
        ([1, 1], [-1.0, 0.5]),  # total wipe-out
        ([0, 1], [0.0, 0.02]),  # trade starts on the last bar
    ],
)
def test_matches_reference_on_edge_cases(position, returns) -> None:
    data = _frame(position, returns)

    pd.testing.assert_series_equal(_trade_returns(data), _reference(data), rtol=0, atol=1e-15)


def test_returns_empty_float_series_when_flat() -> None:
    result = _trade_returns(_frame([0, 0, 0], [0.01, 0.02, 0.03]))

    assert result.empty and result.dtype == float


def test_exit_cost_is_allocated_to_the_closed_trade() -> None:
    data = _frame(
        [0, 1, 1, 0],
        [0.0, 0.005, 0.0, -0.01],
        [0.0, 0.01, 0.0, 0.01],
    )

    result = _trade_returns(data)

    assert result.iloc[0] == pytest.approx((1.005 * 0.99) - 1.0)


def test_reversal_splits_turnover_cost_between_closed_and_new_trade() -> None:
    data = _frame(
        [0, 1, -1, 0],
        [0.0, 0.09, 0.08, -0.01],
        [0.0, 0.01, 0.02, 0.01],
    )

    result = _trade_returns(data)

    assert result.tolist() == pytest.approx([0.0791, 0.0791])
