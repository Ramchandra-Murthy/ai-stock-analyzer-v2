from datetime import UTC, datetime

import pandas as pd
import pytest

from ai_trading.news_schema import NewsRecord
from ai_trading.sentiment_robustness_diagnostics import (
    evaluate_sentiment_robustness_grid,
)


def _news(day: int, score: float = 0.8) -> NewsRecord:
    return NewsRecord(
        title="test headline",
        source="Test",
        symbol="ABC",
        published_at=datetime(2026, 10, 1, 9 + day, tzinfo=UTC),
        sentiment_score=score,
    )


@pytest.fixture
def inputs():
    index = pd.date_range("2026-10-01 09:00", periods=30, freq="h", tz="UTC")
    bars = {"ABC": pd.DataFrame({"Close": [100.0 + i for i in range(30)]}, index=index)}
    records = [_news(day) for day in range(1, 8)]
    return records, bars


def test_robustness_grid_reports_parameter_sensitivity(inputs):
    records, bars = inputs
    result = evaluate_sentiment_robustness_grid(
        records,
        bars,
        horizons=(2, 4),
        sentiment_thresholds=(0.1, 0.5),
        transaction_costs_bps=(5.0, 15.0),
        folds=3,
    )

    assert len(result) == 8
    assert set(result["horizon"]) == {2, 4}
    assert set(result["sentiment_threshold"]) == {0.1, 0.5}
    assert set(result["transaction_cost_bps"]) == {5.0, 15.0}
    assert result["events"].eq(7).all()
    assert result["folds"].eq(3).all()
    assert result["mean_fold_return"].notna().all()
    assert result["worst_fold_drawdown"].le(0.0).all()


def test_robustness_grid_empty_parameter_values_rejected(inputs):
    records, bars = inputs
    with pytest.raises(ValueError, match="non-empty"):
        evaluate_sentiment_robustness_grid(records, bars, horizons=())
