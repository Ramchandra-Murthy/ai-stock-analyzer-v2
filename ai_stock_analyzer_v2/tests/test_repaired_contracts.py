import math

import pandas as pd

from services.ai_service import get_ai_recommendation
from services.fundamental_score_service import calculate_fundamental_score
from services.recommendation_service import generate_recommendation
from services.score_service import calculate_investment_score, calculate_stability_score
from services.target_price_service import calculate_target_price
from services.technical_score_service import calculate_technical_score
from services.trade_plan_service import generate_trade_plan
from services.ui_formatters import (
    format_debt_to_equity,
    format_market_cap,
    format_percent,
    format_price,
    format_ratio,
    safe_progress,
)


def _valid_history(rows=25):
    return pd.DataFrame(
        {
            "High": [101.0 + i for i in range(rows)],
            "Low": [99.0 + i for i in range(rows)],
            "Close": [100.0 + i for i in range(rows)],
        }
    )


def test_technical_score_requires_real_indicator_evidence():
    history = _valid_history()
    score, reasons = calculate_technical_score(history)
    assert score is None
    assert "Insufficient technical indicators for scoring" in reasons


def test_fundamental_score_rejects_extreme_percentage_payloads():
    score, _ = calculate_fundamental_score(
        {
            "roe": 25,
            "roa": 0.05,
            "profit_margin": 0.10,
            "operating_margin": 0.12,
        }
    )
    assert score is not None
    assert 0 <= score <= 100


def test_ai_component_returns_no_score_without_evidence():
    result = get_ai_recommendation({}, None)
    assert result["score"] is None


def test_investment_score_requires_core_evidence():
    score, breakdown = calculate_investment_score(None, 70, ai_result=None, data={})
    assert score is None
    assert breakdown["Score Status"] == "INSUFFICIENT CORE EVIDENCE"


def test_stability_rejects_extreme_ratio_values():
    score, reasons = calculate_stability_score(
        {"beta": 1.0, "debt_to_equity": 10001, "current_ratio": 1.5}
    )
    assert score is not None
    assert any("invalid" in reason.lower() for reason in reasons)


def test_recommendation_rejects_non_finite_scores():
    result = generate_recommendation(float("nan"))
    assert result["recommendation"] == "INSUFFICIENT DATA"
    assert result["overall_score"] is None


def test_target_price_requires_valid_technical_evidence():
    result = calculate_target_price(_valid_history(), technical_score=None)
    assert result["status"] == "Insufficient technical evidence"
    assert result["target_price"] is None


def test_trade_plan_rejects_invalid_ohlc_rows():
    history = _valid_history()
    # Six invalid candles leave only 19 valid observations, below the
    # minimum required for a safe trade plan.
    history.loc[0:5, "High"] = -1
    result = generate_trade_plan(history, technical_score=60)
    assert result["status"] in {"ERROR", "INSUFFICIENT DATA"}


def test_repaired_scores_remain_finite_when_present():
    score, _ = calculate_stability_score({"beta": 1.0})
    assert score is None or math.isfinite(score)


def test_ui_formatters_reject_invalid_evidence():
    assert format_market_cap(float("nan")) == "N/A"
    assert format_market_cap(-1) == "N/A"
    assert format_percent(float("inf")) == "N/A"
    assert format_percent(11) == "N/A"
    assert format_price(0) == "N/A"
    assert format_price(-10) == "N/A"
    assert format_ratio(0) == "N/A"
    assert format_debt_to_equity(-1) == "N/A"
    assert format_debt_to_equity(10001) == "N/A"


def test_ui_progress_rejects_out_of_domain_scores():
    assert safe_progress(float("nan")) == 0.0
    assert safe_progress(-1) == 0.0
    assert safe_progress(101) == 0.0
    assert safe_progress(75) == 0.75
