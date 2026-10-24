import math

import pandas as pd
import pytest

from ai_trading.parameter_robustness import parameter_robustness_summary


def test_parameter_robustness_summarizes_metric_distribution() -> None:
    results = pd.DataFrame(
        {
            "window": [10, 15, 20, 25],
            "sharpe_ratio": [1.0, 1.8, 1.7, -0.2],
        }
    )

    summary = parameter_robustness_summary(
        results,
        parameter_columns=("window",),
        near_best_tolerance=0.10,
    )

    assert summary["configurations"] == 4
    assert summary["best_metric"] == pytest.approx(1.8)
    assert summary["median_metric"] == pytest.approx(1.35)
    assert summary["positive_fraction"] == pytest.approx(0.75)
    assert summary["near_best_fraction"] == pytest.approx(0.5)


def test_parameter_robustness_excludes_non_finite_metrics_and_missing_params() -> None:
    results = pd.DataFrame(
        {
            "window": [10, None, 20, 25],
            "sharpe_ratio": [1.0, 5.0, float("inf"), float("nan")],
        }
    )

    summary = parameter_robustness_summary(results, parameter_columns=("window",))

    assert summary["configurations"] == 1
    assert summary["best_metric"] == pytest.approx(1.0)
    assert math.isfinite(summary["metric_std"])


def test_parameter_robustness_handles_empty_valid_results() -> None:
    results = pd.DataFrame({"sharpe_ratio": [float("inf"), float("nan")]})

    summary = parameter_robustness_summary(results)

    assert summary["configurations"] == 0
    assert summary["best_metric"] is None
    assert summary["near_best_fraction"] is None


@pytest.mark.parametrize("tolerance", [-0.1, 1.0, 2.0])
def test_parameter_robustness_rejects_invalid_tolerance(tolerance: float) -> None:
    with pytest.raises(ValueError, match="near_best_tolerance"):
        parameter_robustness_summary(
            pd.DataFrame({"sharpe_ratio": [1.0, 2.0]}),
            near_best_tolerance=tolerance,
        )


def test_parameter_robustness_requires_metric_column() -> None:
    with pytest.raises(KeyError, match="missing metric column"):
        parameter_robustness_summary(pd.DataFrame({"return": [0.1, 0.2]}))
