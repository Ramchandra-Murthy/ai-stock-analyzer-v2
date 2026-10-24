"""
Module: tests.forecast.algorithms.test_linear_regression
Description: Unit tests for Linear Regression forecast calculation engine.
"""

from __future__ import annotations

import pytest

from services.forecast.algorithms.linear_regression import (
    LinearRegressionForecastEngine,
)


def test_linear_regression_engine_basic() -> None:
    engine = LinearRegressionForecastEngine()
    historical = (10.0, 20.0, 30.0)
    projected = engine.calculate(historical, periods=2)
    assert len(projected) == 2
    assert pytest.approx(projected[0], rel=1e-4) == 40.0
    assert pytest.approx(projected[1], rel=1e-4) == 50.0


def test_linear_regression_engine_edge_cases() -> None:
    engine = LinearRegressionForecastEngine()
    assert engine.calculate((), periods=3) == ()
    assert engine.calculate((50.0,), periods=2) == (50.0, 50.0)
