import pandas as pd
import pytest

from ai_trading.return_distribution import (
    downside_deviation,
    return_distribution_summary,
)


def test_return_distribution_summary_reports_shape_and_tail_fractions():
    returns = pd.Series([-0.02, 0.01, 0.03, -0.01, 0.02])

    result = return_distribution_summary(returns)

    assert result["observations"] == 5.0
    assert result["mean"] == pytest.approx(0.006)
    assert result["positive_fraction"] == pytest.approx(0.6)
    assert result["negative_fraction"] == pytest.approx(0.4)
    assert result["skewness"] is not None
    assert result["kurtosis"] is not None


def test_return_distribution_summary_drops_invalid_values():
    returns = pd.Series([0.01, None, -0.02])

    result = return_distribution_summary(returns)

    assert result["observations"] == 2.0


def test_return_distribution_summary_handles_empty_returns():
    result = return_distribution_summary(pd.Series(dtype=float))

    assert result["observations"] == 0.0
    assert result["mean"] is None


def test_downside_deviation_uses_target_return():
    returns = pd.Series([-0.10, 0.02, -0.04])

    result = downside_deviation(returns, target=0.0)

    assert result == pytest.approx(((0.10**2 + 0.04**2) / 3) ** 0.5)


def test_downside_deviation_handles_empty_returns():
    assert downside_deviation(pd.Series(dtype=float)) == 0.0
