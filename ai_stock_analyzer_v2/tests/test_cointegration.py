import numpy as np
import pandas as pd
import pytest

from ai_trading.cointegration import cadf_diagnostic, johansen_diagnostic


@pytest.fixture
def cointegrated_prices() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    x = 100.0 + np.cumsum(rng.normal(0.0, 1.0, 120))
    stationary = np.zeros(120)
    noise = rng.normal(0.0, 0.5, 120)
    for index in range(1, len(stationary)):
        stationary[index] = 0.7 * stationary[index - 1] + noise[index]
    y = 2.0 * x + stationary
    z = 0.5 * x - stationary
    return pd.DataFrame({"x": x, "y": y, "z": z})


def test_cadf_recovers_hedge_ratio_and_mean_reverting_spread(
    cointegrated_prices: pd.DataFrame,
) -> None:
    report = cadf_diagnostic(
        cointegrated_prices["y"],
        cointegrated_prices["x"],
        lags=1,
    )

    assert report["observations"] == 120
    assert report["hedge_ratio"] == pytest.approx(2.0, abs=0.05)
    assert report["adf_statistic"] is not None
    assert report["adf_statistic"] < 0.0
    assert report["half_life"] is not None
    assert report["half_life"] > 0.0


def test_johansen_reports_ordered_eigenvalues_and_vectors(
    cointegrated_prices: pd.DataFrame,
) -> None:
    report = johansen_diagnostic(cointegrated_prices, lags=1)

    eigenvalues = np.asarray(report["eigenvalues"], dtype=float)
    eigenvectors = np.asarray(report["eigenvectors"], dtype=float)

    assert report["observations"] == 119
    assert report["series"] == 3
    assert eigenvalues.shape == (3,)
    assert eigenvectors.shape == (3, 3)
    assert np.all(np.isfinite(eigenvalues))
    assert np.all((eigenvalues >= 0.0) & (eigenvalues < 1.0))
    assert np.all(np.diff(eigenvalues) <= 0.0)
    assert len(report["trace_statistics"]) == 3
    assert len(report["max_eigen_statistics"]) == 3


@pytest.mark.parametrize(
    ("function", "kwargs"),
    [
        (cadf_diagnostic, {"lags": -1}),
        (johansen_diagnostic, {"lags": 0}),
    ],
)
def test_cointegration_diagnostics_validate_lags(
    function: object,
    kwargs: dict[str, int],
) -> None:
    with pytest.raises(ValueError):
        if function is cadf_diagnostic:
            function(pd.Series([1.0, 2.0, 3.0, 4.0]), pd.Series([1.0, 2.0, 3.0, 4.0]), **kwargs)
        else:
            function(pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [1.0, 2.0, 3.0, 4.0]}), **kwargs)


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf")])
def test_cadf_ignores_non_finite_aligned_observations(
    cointegrated_prices: pd.DataFrame,
    bad_value: float,
) -> None:
    dependent = cointegrated_prices["y"].copy()
    independent = cointegrated_prices["x"].copy()
    dependent.iloc[10] = bad_value

    report = cadf_diagnostic(dependent, independent)

    assert report["observations"] == 119
    assert np.isfinite(report["hedge_ratio"])


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf")])
def test_johansen_ignores_rows_with_non_finite_prices(
    cointegrated_prices: pd.DataFrame,
    bad_value: float,
) -> None:
    contaminated = cointegrated_prices.copy()
    contaminated.iloc[10, 1] = bad_value

    report = johansen_diagnostic(contaminated, lags=1)

    assert report["observations"] == 118
    assert np.all(np.isfinite(np.asarray(report["eigenvalues"], dtype=float)))
    assert np.all(np.isfinite(np.asarray(report["eigenvectors"], dtype=float)))
