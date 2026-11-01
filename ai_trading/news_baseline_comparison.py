"""Compare learned and lexicon sentiment baselines on the same future holdout."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sklearn.metrics import accuracy_score, f1_score

from ai_trading.financial_sentiment_model import build_classifier
from ai_trading.news_schema import NewsRecord
from ai_trading.news_sentiment import score_headline


@dataclass(frozen=True)
class SentimentBaselineComparison:
    """Comparable metrics for model and lexicon predictions on identical records."""

    train_size: int
    test_size: int
    train_end: datetime
    test_start: datetime
    model_accuracy: float
    model_macro_f1: float
    lexicon_accuracy: float
    lexicon_macro_f1: float


def _text(record: NewsRecord) -> str:
    return " ".join(part for part in (record.title, record.summary or "") if part).strip()


def compare_sentiment_baselines(
    records: Sequence[NewsRecord],
    *,
    test_size: float = 0.25,
) -> SentimentBaselineComparison:
    """Compare TF-IDF/logistic regression with the finance lexicon chronologically.

    The model is fit only on the earlier training period. Both approaches are
    scored on exactly the same later records, making metrics directly comparable.
    """
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1")
    if len(records) < 4:
        raise ValueError("At least four labeled news records are required")

    rows: list[tuple[datetime, str, str]] = []
    for record in records:
        if not record.sentiment_label:
            raise ValueError("Every evaluation record must have a sentiment_label")
        label = record.sentiment_label.upper()
        if label not in {"POSITIVE", "NEGATIVE", "NEUTRAL"}:
            raise ValueError(f"Unsupported sentiment label: {label}")
        text = _text(record)
        if not text:
            raise ValueError("Evaluation records must contain title or summary text")
        rows.append((record.published_at, text, label))

    rows.sort(key=lambda row: row[0])
    split = max(1, min(int(len(rows) * (1.0 - test_size)), len(rows) - 1))
    while split < len(rows) and rows[split][0] == rows[split - 1][0]:
        split += 1
    if split >= len(rows):
        raise ValueError("Not enough distinct publication times for a chronological split")

    train, test = rows[:split], rows[split:]
    train_labels = [row[2] for row in train]
    if len(set(train_labels)) < 2:
        raise ValueError("Chronological training period must contain at least two classes")

    model = build_classifier()
    model.fit([row[1] for row in train], train_labels)
    y_true = [row[2] for row in test]
    model_predictions = model.predict([row[1] for row in test])
    lexicon_predictions = [score_headline(row[1]).label for row in test]

    return SentimentBaselineComparison(
        train_size=len(train),
        test_size=len(test),
        train_end=train[-1][0],
        test_start=test[0][0],
        model_accuracy=float(accuracy_score(y_true, model_predictions)),
        model_macro_f1=float(f1_score(y_true, model_predictions, average="macro", zero_division=0)),
        lexicon_accuracy=float(accuracy_score(y_true, lexicon_predictions)),
        lexicon_macro_f1=float(
            f1_score(y_true, lexicon_predictions, average="macro", zero_division=0)
        ),
    )
