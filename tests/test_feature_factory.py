import pandas as pd
import pytest

from ai_trading.feature_factory import build_ai_feature_frame, latest_ai_features
from ai_trading.fundamental_intelligence import normalize_fundamentals


def _frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=30, freq="D")
    return pd.DataFrame(
        {
            "Close": range(100, 130),
            "Volume": range(1000, 1030),
        },
        index=index,
    )


def test_feature_factory_combines_market_fundamental_and_news_features() -> None:
    fundamentals = normalize_fundamentals({"revenue_growth_pct": 10, "debt_to_equity": 0.5})
    features = build_ai_feature_frame(
        _frame(),
        fundamentals=fundamentals,
        sentiment_score=0.25,
    )

    assert not features.empty
    assert features.iloc[-1]["fundamental_revenue_growth_pct"] == pytest.approx(10.0)
    assert features.iloc[-1]["fundamental_debt_to_equity"] == pytest.approx(0.5)
    assert features.iloc[-1]["news_sentiment_score"] == pytest.approx(0.25)


def test_latest_ai_features_returns_latest_row() -> None:
    latest = latest_ai_features(_frame(), sentiment_score=-0.2)
    assert latest["news_sentiment_score"] == pytest.approx(-0.2)


def test_empty_input_is_safe() -> None:
    result = build_ai_feature_frame(pd.DataFrame())
    assert result.empty
