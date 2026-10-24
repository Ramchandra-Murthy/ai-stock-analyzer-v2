"""
Module: tests.forecast.algorithms.test_cagr
Description: Unit tests for CAGR forecast calculation engine.
"""

from __future__ import annotations

import pytest

from services.forecast.algorithms.cagr import CAGRForecastEngine


def test_cagr_engine_basic() -> None:
    engine = CAGRForecastEngine()
    historical = (100.0, 110.0, 121.0)
    projected = engine.calculate(historical, periods=2)
    assert len(projected) == 2
    assert pytest.approx(projected[0], rel=1e-4) == 133.1
    assert pytest.approx(projected[1], rel=1e-4) == 146.41


def test_cagr_engine_edge_cases() -> None:
    engine = CAGRForecastEngine()
    assert engine.calculate((), periods=3) == ()
    assert engine.calculate((100.0,), periods=2) == (100.0, 100.0)
