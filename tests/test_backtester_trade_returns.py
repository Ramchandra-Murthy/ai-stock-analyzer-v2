"""The vectorised ``_trade_returns`` must match the original groupby-apply exactly."""

import numpy as np
import pandas as pd
import pytest

from algorithmic_trading.backtester import _trade_returns


def _reference(data: pd.DataFrame) -> pd.Series:
    """The original implementation (slow Python lambda per trade), kept as the oracle."""
    position = data["position"]
    active = position.ne(0)
    starts = active & (~active.shift(1, fill_value=False) | position.ne(position.shift(1)))
    trade_id = starts.cumsum()
    active_returns = data.loc[active, "strategy_return"]
    if active_returns.empty:
        return pd.Series(dtype=float)
    return active_returns.groupby(trade_id.loc[active]).apply(
        lambda values: (1.0 + values).prod() - 1.0
    )


def _frame(position, returns) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-01", periods=len(position))
    return pd.DataFrame(
        {"position": np.asarray(position, float), "strategy_return": np.asarray(returns, float)},
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
