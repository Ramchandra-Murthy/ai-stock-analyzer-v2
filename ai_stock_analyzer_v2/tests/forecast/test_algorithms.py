"""
Module: tests.forecast.test_algorithms
Description: Comprehensive unit tests for financial forecasting calculation engines.
Author: Engineering Team
Python Version: 3.13+
"""

from __future__ import annotations

import pytest

from services.forecast.algorithms.cagr import CAGRForecastEngine
from services.forecast.algorithms.linear_regression import (
    LinearRegressionForecastEngine,
)
from services.forecast.algorithms.rolling_average import RollingAverageForecastEngine


def test_cagr_engine_basic() -> None:
    """Verify standard CAGR projection behavior."""
    engine = CAGRForecastEngine()
    historical = (100.0, 110.0, 121.0)  # 10% annual growth
    projected = engine.calculate(historical, periods=2)

    assert len(projected) == 2
    # 121 * 1.10 = 133.1, then 133.1 * 1.10 = 146.41
    assert pytest.approx(projected[0], rel=1e-4) == 133.1
    assert pytest.approx(projected[1], rel=1e-4) == 146.41


def test_cagr_engine_edge_cases() -> None:
    """Verify CAGR handling of edge cases (empty, single point, zero values)."""
    engine = CAGRForecastEngine()

    assert engine.calculate((), periods=3) == ()
    assert engine.calculate((100.0,), periods=2) == (100.0, 100.0)

    # Negative/zero start value fallback
    res = engine.calculate((0.0, 100.0), periods=2)
    assert len(res) == 2


def test_linear_regression_engine_basic() -> None:
    """Verify OLS linear regression slope and intercept projections."""
    engine = LinearRegressionForecastEngine()
    historical = (10.0, 20.0, 30.0)  # Perfect linear trend (+10 per period)
    projected = engine.calculate(historical, periods=2)

    assert len(projected) == 2
    assert pytest.approx(projected[0], rel=1e-4) == 40.0
    assert pytest.approx(projected[1], rel=1e-4) == 50.0


def test_linear_regression_engine_edge_cases() -> None:
    """Verify linear regression edge cases and zero variance."""
    engine = LinearRegressionForecastEngine()

    assert engine.calculate((), periods=3) == ()
    assert engine.calculate((50.0,), periods=2) == (50.0, 50.0)

    # Zero variance (flat line)
    flat = (25.0, 25.0, 25.0)
    res = engine.calculate(flat, periods=2)
    assert res == (25.0, 25.0)


def test_rolling_average_engine_basic() -> None:
    """Verify rolling average calculations and custom window sizes."""
    engine = RollingAverageForecastEngine()
    historical = (10.0, 20.0, 30.0, 40.0)

    # Using window_size=2 on tail (30, 40) -> average is 35.0
    projected = engine.calculate(historical, periods=2, window_size=2)
    assert len(projected) == 2
    assert projected == (35.0, 35.0)


def test_rolling_average_engine_edge_cases() -> None:
    """Verify rolling average edge cases."""
    engine = RollingAverageForecastEngine()

    assert engine.calculate((), periods=3) == ()

    # Default window uses full history
    res = engine.calculate((10.0, 20.0), periods=1)
    assert res == (15.0,)
