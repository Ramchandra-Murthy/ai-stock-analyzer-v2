from __future__ import annotations

import pytest

from core.enums import Status, ValuationMethod
from services.research.target_price import TargetPriceCalculator, TargetPriceOutput
from services.sotp.sotp_engine import (
    SegmentValuation,
    SOTPAggregator,
    SOTPInput,
    SOTPResult,
)


@pytest.fixture
def sample_sotp_input() -> SOTPInput:
    segments = [
        SegmentValuation("Infrastructure", ValuationMethod.DCF, 120000.0, 1.00, "Core EPC"),
        SegmentValuation(
            "Financial Services",
            ValuationMethod.COMPARABLE,
            35000.0,
            0.66,
            "Financial subsidiary",
        ),
        SegmentValuation("Real Estate", ValuationMethod.NAV, 15000.0, 1.00, "Land bank"),
    ]
    return SOTPInput("Larsen & Toubro", "INR", segments, 0.10, 25000.0, 140.0)


def test_sotp_aggregation_calculation(sample_sotp_input):
    aggregator = SOTPAggregator()
    result: SOTPResult = aggregator.calculate(sample_sotp_input)
    assert result.gross_enterprise_value == pytest.approx(158100.0, abs=1.0)
    assert result.net_equity_value == pytest.approx(119790.0, abs=1.0)
    assert result.value_per_share == pytest.approx(855.64, abs=1e-2)
    assert result.status == Status.OK


def test_target_price_weighting():
    method_values = {
        ValuationMethod.DCF: 2400.0,
        ValuationMethod.COMPARABLE: 2200.0,
        ValuationMethod.NAV: 2000.0,
    }
    weights = {
        ValuationMethod.DCF: 0.50,
        ValuationMethod.COMPARABLE: 0.30,
        ValuationMethod.NAV: 0.20,
    }
    tp_calc = TargetPriceCalculator()
    output: TargetPriceOutput = tp_calc.compute_target_price(
        "LT.NS", 1800.0, method_values, weights, 0.10
    )
    assert output.weighted_fair_value == pytest.approx(2260.0, abs=1.0)
    assert output.target_price == pytest.approx(2034.0, abs=1.0)
