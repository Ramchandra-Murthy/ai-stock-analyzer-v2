from datetime import UTC, datetime

import pandas as pd
import pytest

from ai_trading.news_schema import NewsRecord
from ai_trading.sentiment_walk_forward_backtest import evaluate_sentiment_walk_forward


def _news(symbol: str, score: float, day: int) -> NewsRecord:
    return NewsRecord(
        title="test headline",
        source="Test",
        symbol=symbol,
        published_at=datetime(2026, 10, day, 9, tzinfo=UTC),
        sentiment_score=score,
    )


@pytest.fixture
def bars() -> dict[str, pd.DataFrame]:
    index = pd.date_range("2026-10-01 09:00", periods=20, freq="h", tz="UTC")
    return {"ABC": pd.DataFrame({"Close": [100.0 + i for i in range(20)]}, index=index)}


def test_sentiment_walk_forward_is_chronological_and_cost_adjusted(bars):
    records = [_news("ABC", 0.8, 1), _news("ABC", -0.8, 2), _news("ABC", 0.7, 3)]
    result = evaluate_sentiment_walk_forward(
        records, bars, horizon=2, folds=2, transaction_cost_bps=5
    )

    assert len(result.events) == 3
    assert result.events["published_at"].is_monotonic_increasing
    assert result.events["net_return"].lt(result.events["gross_return"]).all()
    assert result.events["fold"].tolist() == [1, 1, 2]
    assert len(result.folds) == 2


def test_skips_neutral_missing_score_and_unknown_symbol(bars):
    records = [
        _news("ABC", 0.01, 1),
        _news("ABC", 0.8, 2),
        _news("MISSING", 0.9, 3),
        NewsRecord(
            title="no score",
            source="Test",
            symbol="ABC",
            published_at=datetime(2026, 10, 4, 9, tzinfo=UTC),
        ),
    ]
    result = evaluate_sentiment_walk_forward(records, bars, sentiment_threshold=0.1)

    assert len(result.events) == 1
    assert result.events.iloc[0]["signal"] == "LONG"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"horizon": 0}, "horizon"),
        ({"folds": 1}, "folds"),
        ({"sentiment_threshold": 1.1}, "sentiment_threshold"),
        ({"transaction_cost_bps": -1}, "transaction_cost"),
    ],
)
def test_rejects_invalid_parameters(bars, kwargs, message):
    with pytest.raises(ValueError, match=message):
        evaluate_sentiment_walk_forward([_news("ABC", 0.8, 1)], bars, **kwargs)


def test_rejects_naive_bar_timestamps():
    frame = pd.DataFrame(
        {"Close": [100.0, 101.0]},
        index=pd.date_range("2026-10-01", periods=2, freq="h"),
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_sentiment_walk_forward([_news("ABC", 0.8, 1)], {"ABC": frame})
