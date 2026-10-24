import pandas as pd
import pytest

from algorithmic_trading.edge_engine import calculate_edge
from algorithmic_trading.signal_engine import compose_signal


def test_bullish_signal_uses_all_components() -> None:
    edge = calculate_edge(pd.Series([2.0, 3.0, -1.0]))
    signal = compose_signal("BULLISH", 4, 8.0, edge, min_expectancy=0.5)
    assert signal.direction == "LONG"
    assert signal.edge_qualified is True
    assert signal.score == pytest.approx(88.0)


def test_bearish_signal_can_be_offset_by_positive_relative_strength() -> None:
    signal = compose_signal("BEARISH", -3, 30.0)
    assert signal.direction == "FLAT"
    assert signal.score == pytest.approx(-15.0)


def test_inconclusive_regime_cannot_create_directional_signal() -> None:
    signal = compose_signal("INCONCLUSIVE", 2, 30.0)
    assert signal.direction == "FLAT"
    assert signal.score == pytest.approx(60.0)


def test_missing_edge_does_not_claim_edge_qualification() -> None:
    signal = compose_signal("BULLISH", 3)
    assert signal.edge_qualified is False
    assert signal.expectancy is None
