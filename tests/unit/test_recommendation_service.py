from services.recommendation_service import generate_recommendation


def test_recommendation_bands():
    assert generate_recommendation(90)["recommendation"] == "STRONG BUY"
    assert generate_recommendation(70)["recommendation"] == "BUY"
    assert generate_recommendation(55)["recommendation"] == "HOLD"
    assert generate_recommendation(40)["recommendation"] == "SELL"
    assert generate_recommendation(39)["recommendation"] == "STRONG SELL"


def test_recommendation_clamps_score():
    assert generate_recommendation(150)["overall_score"] == 100
    assert generate_recommendation(-10)["overall_score"] == 0


def test_recommendation_missing_data_is_not_hold():
    result = generate_recommendation(None)
    assert result["recommendation"] == "INSUFFICIENT DATA"
    assert result["confidence"] is None
    assert result["overall_score"] is None


def test_recommendation_invalid_data_is_not_hold():
    result = generate_recommendation("not-a-score")
    assert result["recommendation"] == "INSUFFICIENT DATA"
    assert result["confidence"] is None
    assert result["overall_score"] is None
