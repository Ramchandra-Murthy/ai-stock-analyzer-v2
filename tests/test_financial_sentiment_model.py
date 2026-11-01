from datetime import UTC, datetime

import pytest

from ai_trading.financial_sentiment_model import (
    MODEL_VERSION,
    evaluate_classifier,
    predict_sentiment,
    train_classifier,
)
from ai_trading.news_schema import NewsRecord


def _record(title: str, label: str) -> NewsRecord:
    return NewsRecord(
        title=title,
        source="Test",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
        sentiment_label=label,
    )


@pytest.fixture
def labeled_records() -> list[NewsRecord]:
    return [
        _record("Company reports record profit growth", "POSITIVE"),
        _record("Strong revenue and earnings beat estimates", "POSITIVE"),
        _record("Shares rise after upbeat results", "POSITIVE"),
        _record("Business wins major new contract", "POSITIVE"),
        _record("Company reports quarterly loss", "NEGATIVE"),
        _record("Revenue falls and outlook is weak", "NEGATIVE"),
        _record("Shares decline after disappointing results", "NEGATIVE"),
        _record("Regulator investigates accounting concerns", "NEGATIVE"),
        _record("Company announces board meeting date", "NEUTRAL"),
        _record("Firm schedules investor conference", "NEUTRAL"),
        _record("Company publishes routine filing", "NEUTRAL"),
        _record("Exchange announces trading holiday", "NEUTRAL"),
    ]


def test_train_and_predict_returns_valid_label_and_confidence(
    labeled_records: list[NewsRecord],
) -> None:
    model = train_classifier(labeled_records)
    prediction = predict_sentiment(
        model, _record("Company posts strong earnings growth", "POSITIVE")
    )

    assert prediction.label in {"POSITIVE", "NEGATIVE", "NEUTRAL"}
    assert 0.0 <= prediction.confidence <= 1.0
    assert prediction.model_version == MODEL_VERSION


def test_evaluation_returns_metrics_and_three_class_matrix(
    labeled_records: list[NewsRecord],
) -> None:
    result = evaluate_classifier(labeled_records)

    assert 0.0 <= result.accuracy <= 1.0
    assert 0.0 <= result.macro_f1 <= 1.0
    assert result.test_size == 3
    assert len(result.confusion_matrix) == 3
    assert all(len(row) == 3 for row in result.confusion_matrix)
    assert "macro avg" in result.classification_report


def test_training_rejects_unlabeled_records() -> None:
    unlabeled = NewsRecord(
        title="Unlabeled headline",
        source="Test",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="sentiment_label"):
        train_classifier([_record("Headline", "POSITIVE"), unlabeled])


def test_evaluation_requires_two_examples_per_class() -> None:
    records = [
        _record("Positive news", "POSITIVE"),
        _record("Negative news", "NEGATIVE"),
        _record("Neutral news", "NEUTRAL"),
    ]
    with pytest.raises(ValueError, match="at least two"):
        evaluate_classifier(records)
