import pandas as pd

from services.ai_service import get_ai_recommendation


def test_ai_service_returns_component_only():
    result = get_ai_recommendation(
        {"pe": 15, "eps": 2, "profit_margin": 0.2, "roe": 0.2, "beta": 0.8},
        pd.DataFrame({"Close": [110], "EMA200": [100]}),
    )

    assert 0 <= result["score"] <= 100
    assert result["component"] == "AI"
    assert "recommendation" not in result
    assert "risk" not in result


def test_ai_service_returns_no_score_for_only_invalid_values():
    result = get_ai_recommendation({"pe": float("nan"), "eps": "bad"})

    assert result["score"] is None
    assert result["reasons"] == ["Insufficient AI evidence; no score calculated"]
