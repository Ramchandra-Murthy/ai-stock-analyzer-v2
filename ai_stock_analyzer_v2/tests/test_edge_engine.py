import pandas as pd
import pytest

from algorithmic_trading.edge_engine import calculate_edge, rolling_expectancy


def test_calculate_edge() -> None:
    metrics = calculate_edge(pd.Series([2.0, 4.0, -1.0, -3.0]))
    assert metrics.trades == 4
    assert metrics.win_rate == pytest.approx(0.5)
    assert metrics.average_win == pytest.approx(3.0)
    assert metrics.average_loss == pytest.approx(2.0)
    assert metrics.expectancy == pytest.approx(0.5)
    assert metrics.profit_factor == pytest.approx(1.5)


def test_empty_returns_are_safe() -> None:
    metrics = calculate_edge(pd.Series(dtype=float))
    assert metrics.trades == 0
    assert metrics.expectancy == 0.0
    assert metrics.profit_factor is None


def test_rolling_expectancy() -> None:
    result = rolling_expectancy(pd.Series([1.0, -1.0, 2.0]), window=2)
    assert pd.isna(result.iloc[0])
    assert result.iloc[1] == pytest.approx(0.0)
    assert result.iloc[2] == pytest.approx(0.5)


def test_invalid_window_fails() -> None:
    with pytest.raises(ValueError, match="window"):
        rolling_expectancy(pd.Series([1.0]), window=0)
