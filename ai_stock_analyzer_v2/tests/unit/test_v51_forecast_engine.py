import pytest

from services.forecast.assumption_engine import AssumptionEngine, ManagementGuidance
from services.forecast.confidence_engine import ConfidenceEngine, ConfidenceLevel
from services.forecast.terminal_growth import TerminalGrowthEngine, TerminalGrowthForecast


def test_confidence_engine_returns_supported_level():
    # The current confidence API accepts one data series and returns a level enum.
    stable_revs = (100.0, 105.0, 110.0, 115.0, 121.0)
    result = ConfidenceEngine.evaluate_confidence(stable_revs)
    assert result in list(ConfidenceLevel)


def test_terminal_growth_forecast_contract():
    # The current engine exposes forecast_terminal_growth and returns a forecast model.
    result = TerminalGrowthEngine().forecast_terminal_growth(None)
    assert isinstance(result, TerminalGrowthForecast)
    assert result.terminal_growth_rate == pytest.approx(0.04)


def test_assumption_engine_overrides():
    engine = AssumptionEngine()
    base_revs = [100.0, 110.0, 120.0]
    base_margins = [0.15, 0.15, 0.15]

    guidance = ManagementGuidance(revenue_cagr_override=0.20, target_ebit_margin_override=0.18)
    adj_revs, adj_margins = engine.apply_overrides(base_revs, base_margins, guidance)

    assert adj_margins[0] == 0.18
    assert adj_revs[1] > base_revs[1]
