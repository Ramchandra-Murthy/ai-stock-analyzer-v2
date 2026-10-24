"""Tests for prediction stability diagnostics."""

import pandas as pd
import pytest

from ai_trading.prediction_stability import (
    prediction_stability,
    prediction_stability_report,
)


def test_prediction_stability_measures_dispersion_and_direction_flips() -> None:
    result = prediction_stability(pd.Series([0.60, 0.65, 0.40, 0.45]))

    assert result["observations"] == 4
    assert result["mean_probability"] == pytest.approx(0.525)
    assert result["probability_std"] == pytest.approx(0.1030776406404415)
    assert result["directional_flips"] == 1
    assert result["directional_agreement"] == pytest.approx(2.0 / 3.0)


def test_prediction_stability_report_classifies_low_dispersion() -> None:
    result = prediction_stability_report(
        pd.Series([0.60, 0.61, 0.59]),
        max_std=0.01,
    )

    assert result["stable"] is True
    assert result["directional_flips"] == 0


def test_prediction_stability_rejects_probability_outside_range() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        prediction_stability(pd.Series([0.5, 1.2]))


def test_prediction_stability_handles_empty_series() -> None:
    result = prediction_stability(pd.Series(dtype=float))

    assert result["observations"] == 0
    assert result["mean_probability"] is None
    assert result["directional_flips"] == 0
