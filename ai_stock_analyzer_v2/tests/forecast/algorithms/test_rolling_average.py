"""
Module: tests.forecast.algorithms.test_rolling_average
Description: Unit tests for Rolling Average forecast calculation engine.
"""

from __future__ import annotations

from services.forecast.algorithms.rolling_average import RollingAverageForecastEngine


def test_rolling_average_engine_basic() -> None:
    engine = RollingAverageForecastEngine()
    historical = (10.0, 20.0, 30.0, 40.0)
    projected = engine.calculate(historical, periods=2, window_size=2)
    assert len(projected) == 2
    assert projected == (35.0, 35.0)


def test_rolling_average_engine_edge_cases() -> None:
    engine = RollingAverageForecastEngine()
    assert engine.calculate((), periods=3) == ()
