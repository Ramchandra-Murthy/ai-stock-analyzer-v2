import math
from collections.abc import Callable

import pandas as pd
import pytest

from ai_trading.mean_reversion import (
    adf_diagnostic,
    hurst_exponent,
    mean_reversion_half_life,
    mean_reversion_summary,
    variance_ratio,
)


@pytest.fixture
def mean_reverting_series() -> pd.Series:
    return pd.Series(
        [
            100.0,
            90.0,
            95.0,
            92.0,
            94.0,
            93.0,
            93.5,
            93.2,
            93.4,
            93.3,
            93.35,
            93.32,
        ]
    )


def test_adf_diagnostic_reports_negative_mean_reversion_coefficient(
    mean_reverting_series: pd.Series,
) -> None:
    report = adf_diagnostic(mean_reverting_series, lags=1)

    assert report["observations"] == 10
    assert report["lambda"] < 0.0
    assert report["adf_statistic"] is not None
    assert report["adf_statistic"] < 0.0


def test_hurst_and_variance_ratio_return_finite_values(
    mean_reverting_series: pd.Series,
) -> None:
    hurst = hurst_exponent(mean_reverting_series)
    ratio = variance_ratio(mean_reverting_series, lag=2)

    assert math.isfinite(hurst)
    assert math.isfinite(ratio)
    assert ratio >= 0.0


def test_half_life_is_positive_for_mean_reverting_series(
    mean_reverting_series: pd.Series,
) -> None:
    half_life = mean_reversion_half_life(mean_reverting_series)

    assert half_life is not None
    assert half_life > 0.0


def test_mean_reversion_summary_combines_four_diagnostics(
    mean_reverting_series: pd.Series,
) -> None:
    summary = mean_reversion_summary(
        mean_reverting_series,
        adf_lags=1,
        variance_ratio_lag=2,
    )

    assert summary["observations"] == 10
    assert summary["adf_statistic"] is not None
    assert summary["adf_lambda"] is not None
    assert summary["hurst_exponent"] is not None
    assert summary["variance_ratio"] is not None
    assert summary["half_life"] is not None


@pytest.mark.parametrize(
    ("function", "kwargs"),
    [
        (adf_diagnostic, {"lags": -1}),
        (hurst_exponent, {"min_lag": 1}),
        (variance_ratio, {"lag": 1}),
    ],
)
def test_mean_reversion_diagnostics_validate_parameters(
    function: Callable[..., object],
    kwargs: dict[str, int],
) -> None:
    with pytest.raises(ValueError):
        function(pd.Series([100.0, 101.0, 102.0]), **kwargs)


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf")])
def test_mean_reversion_diagnostics_ignore_non_finite_observations(
    mean_reverting_series: pd.Series,
    bad_value: float,
) -> None:
    contaminated = pd.concat([mean_reverting_series, pd.Series([bad_value])], ignore_index=True)

    assert math.isfinite(hurst_exponent(contaminated))
    assert math.isfinite(variance_ratio(contaminated, lag=2))


@pytest.mark.parametrize("function", [hurst_exponent, variance_ratio])
@pytest.mark.parametrize("bad_value", [0.0, -1.0])
def test_log_price_diagnostics_reject_non_positive_observations(
    function: Callable[..., object],
    bad_value: float,
) -> None:
    values = pd.Series([100.0, 101.0, bad_value, 102.0, 103.0, 104.0])

    with pytest.raises(ValueError, match="strictly positive"):
        function(values)
