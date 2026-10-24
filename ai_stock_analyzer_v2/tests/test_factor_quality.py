import numpy as np
import pandas as pd
import pytest

from engine.factor_quality import evaluate_factor_quality


def test_factor_quality_summarizes_daily_spearman_ic_by_horizon():
    factor = pd.DataFrame(
        [[1, 2, 3, 4], [4, 3, 2, 1], [1, 2, 3, 4]],
        index=[1, 2, 3],
        columns=list("ABCD"),
    )
    returns = pd.DataFrame(
        [[0.01, 0.02, 0.03, 0.04], [0.01, 0.02, 0.03, 0.04], [0.01, 0.02, 0.03, 0.04]],
        index=[1, 2, 3],
        columns=list("ABCD"),
    )

    result = evaluate_factor_quality(factor, {5: returns, 20: returns})

    assert result["Horizon"].tolist() == [5, 20]
    assert result["Observations"].tolist() == [3, 3]
    assert result["Mean IC"].tolist() == pytest.approx([1 / 3, 1 / 3])
    assert result["Positive IC Rate"].tolist() == pytest.approx([2 / 3, 2 / 3])
    assert np.isfinite(result.loc[0, "ICIR"])


def test_factor_quality_ignores_dates_with_too_few_valid_pairs():
    factor = pd.DataFrame([[1, 2, 3], [1, np.nan, np.nan]], index=[1, 2])
    returns = pd.DataFrame([[3, 2, 1], [1, 2, 3]], index=[1, 2])

    result = evaluate_factor_quality(factor, {1: returns}, min_assets=3)

    assert result.loc[0, "Observations"] == 1
    assert result.loc[0, "Mean IC"] == pytest.approx(-1.0)


def test_factor_quality_returns_nan_metrics_when_no_valid_cross_sections():
    factor = pd.DataFrame([[1, 1, 1]], columns=list("ABC"))
    returns = pd.DataFrame([[0.1, 0.2, 0.3]], columns=list("ABC"))

    result = evaluate_factor_quality(factor, {1: returns})

    assert result.loc[0, "Observations"] == 0
    assert np.isnan(result.loc[0, "Mean IC"])
    assert np.isnan(result.loc[0, "Positive IC Rate"])


@pytest.mark.parametrize("min_assets", [0, 1, True, 2.5])
def test_factor_quality_rejects_invalid_min_assets(min_assets):
    with pytest.raises(ValueError, match="min_assets"):
        evaluate_factor_quality(
            pd.DataFrame([[1, 2, 3]]),
            {1: pd.DataFrame([[3, 2, 1]])},
            min_assets=min_assets,
        )


@pytest.mark.parametrize("horizon", [0, -1, True, 1.5])
def test_factor_quality_rejects_invalid_horizons(horizon):
    with pytest.raises(ValueError, match="horizons"):
        evaluate_factor_quality(
            pd.DataFrame([[1, 2, 3]]),
            {horizon: pd.DataFrame([[3, 2, 1]])},
        )


def test_factor_quality_rejects_duplicate_factor_indexes():
    factor = pd.DataFrame([[1, 2, 3], [2, 3, 4]], index=[1, 1])
    returns = pd.DataFrame([[3, 2, 1], [4, 3, 2]], index=[1, 2])

    with pytest.raises(ValueError, match="unique"):
        evaluate_factor_quality(factor, {1: returns})
