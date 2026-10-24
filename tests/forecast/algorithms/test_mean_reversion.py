"""
==========================================================
TEST MEAN REVERSION FORECAST ALGORITHM
Module  : tests.forecast.algorithms.test_mean_reversion
Layer   : Tests / Forecast / Algorithms
==========================================================
"""

from __future__ import annotations

import pytest

from services.forecast.algorithms.mean_reversion import MeanReversionCalculator
from services.forecast.exceptions import ValuationError


def test_mean_reversion_convergence() -> None:
    # Historical: 10, 20, 30 (mean = 20, last = 30)
    # Projections should pull down toward 20
    history = (10.0, 20.0, 30.0)
    projections = MeanReversionCalculator.project(history, horizon=2, reversion_speed=0.5)
    assert len(projections) == 2
    assert projections[0] < 30.0  # Pulled down toward mean
    assert projections[1] < projections[0]  # Continues converging


def test_mean_reversion_insufficient_data_raises() -> None:
    with pytest.raises(ValuationError, match="At least 2 periods"):
        MeanReversionCalculator.project((10.0,), horizon=2)


def test_mean_reversion_invalid_speed_raises() -> None:
    with pytest.raises(ValuationError, match="Reversion speed must be between"):
        MeanReversionCalculator.project((10.0, 20.0), horizon=2, reversion_speed=1.5)
