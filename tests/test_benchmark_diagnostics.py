"""Tests for benchmark-relative performance diagnostics."""

import pandas as pd
import pytest

from ai_trading.benchmark_diagnostics import benchmark_relative_diagnostics


def test_benchmark_relative_diagnostics_measures_active_return_and_tracking_error() -> None:
    strategy = pd.Series([0.02, -0.01, 0.03])
    benchmark = pd.Series([0.01, 0.00, 0.02])

    result = benchmark_relative_diagnostics(strategy, benchmark, periods_per_year=252)

    assert result["observations"] == 3
    assert result["active_return"] == pytest.approx((1.02 * 0.99 * 1.03) - (1.01 * 1.00 * 1.02))
    assert result["tracking_error"] == pytest.approx(
        pd.Series([0.01, -0.01, 0.01]).std(ddof=1) * 252**0.5
    )
    assert result["information_ratio"] == pytest.approx(
        pd.Series([0.01, -0.01, 0.01]).mean() * 252 / result["tracking_error"]
    )


def test_benchmark_relative_diagnostics_handles_empty_input() -> None:
    result = benchmark_relative_diagnostics(
        pd.Series(dtype=float),
        pd.Series(dtype=float),
    )

    assert result["observations"] == 0
    assert result["active_return"] is None
    assert result["tracking_error"] is None
    assert result["information_ratio"] is None


def test_benchmark_relative_diagnostics_rejects_invalid_frequency() -> None:
    with pytest.raises(ValueError, match="periods_per_year"):
        benchmark_relative_diagnostics(
            pd.Series([0.01]),
            pd.Series([0.00]),
            periods_per_year=0,
        )
