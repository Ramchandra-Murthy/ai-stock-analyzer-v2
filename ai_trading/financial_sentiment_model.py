"""Baseline financial-news sentiment classifier for offline research.

This module intentionally does not connect to scanners, portfolio decisions, or order
execution. Train only on human-labeled records and evaluate on a held-out split.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ai_trading.news_schema import NewsRecord

SENTIMENT_LABELS = ("NEGATIVE", "NEUTRAL", "POSITIVE")
MODEL_VERSION = "tfidf-logreg-v1"


@dataclass(frozen=True)
class SentimentPrediction:
    """Predicted sentiment and model confidence for one news item."""

    label: str
    confidence: float
    model_version: str = MODEL_VERSION


@dataclass(frozen=True)
class SentimentEvaluation:
    """Held-out classification metrics and class-level diagnostics."""

    accuracy: float
    macro_f1: float
    labels: tuple[str, ...]
    confusion_matrix: list[list[int]]
    classification_report: dict[str, object]
    test_size: int


def _record_text(record: NewsRecord) -> str:
    """Combine available headline and summary text without using future market data."""
    parts = [record.title]
    if record.summary:
        parts.append(record.summary)
    return " ".join(parts).strip()


def _validated_training_data(records: Sequence[NewsRecord]) -> tuple[list[str], list[str]]:
    if len(records) < 2:
        raise ValueError("At least two labeled news records are required")

    texts: list[str] = []
    labels: list[str] = []
    for record in records:
        if not record.sentiment_label:
            raise ValueError("Every training record must have a sentiment_label")
        label = record.sentiment_label.upper()
        if label not in SENTIMENT_LABELS:
            raise ValueError(f"Unsupported sentiment label: {label}")
        text = _record_text(record)
        if not text:
            raise ValueError("Training records must contain title or summary text")
        texts.append(text)
        labels.append(label)

    if len(set(labels)) < 2:
        raise ValueError("Training data must contain at least two sentiment classes")
    return texts, labels


def build_classifier() -> Pipeline:
    """Create a deterministic TF-IDF + Logistic Regression baseline."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    max_features=50_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1_000,
                    random_state=42,
                ),
            ),
        ]
    )


def train_classifier(records: Sequence[NewsRecord]) -> Pipeline:
    """Fit the baseline model on labeled records supplied by the caller."""
    texts, labels = _validated_training_data(records)
    model = build_classifier()
    model.fit(texts, labels)
    return model


def predict_sentiment(model: Pipeline, record: NewsRecord) -> SentimentPrediction:
    """Predict one record; confidence is the maximum class probability."""
    text = _record_text(record)
    if not text:
        raise ValueError("News record must contain title or summary text")
    probabilities = model.predict_proba([text])[0]
    classes = model.named_steps["classifier"].classes_
    best_index = int(probabilities.argmax())
    return SentimentPrediction(
        label=str(classes[best_index]),
        confidence=float(probabilities[best_index]),
    )


def evaluate_classifier(
    records: Sequence[NewsRecord],
    *,
    test_size: float = 0.25,
    random_state: int = 42,
) -> SentimentEvaluation:
    """Evaluate with a stratified holdout; each class needs at least two samples."""
    texts, labels = _validated_training_data(records)
    counts = {label: labels.count(label) for label in set(labels)}
    if min(counts.values()) < 2:
        raise ValueError("Each sentiment class needs at least two records for holdout evaluation")
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1")

    test_count = max(len(counts), int(round(len(records) * test_size)))
    if test_count >= len(records):
        raise ValueError("Not enough records for a stratified train/test split")

    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts,
        labels,
        test_size=test_count,
        random_state=random_state,
        stratify=labels,
    )
    model = build_classifier()
    model.fit(train_texts, train_labels)
    predictions = model.predict(test_texts)
    label_order = tuple(sorted(set(labels)))

    return SentimentEvaluation(
        accuracy=float(accuracy_score(test_labels, predictions)),
        macro_f1=float(f1_score(test_labels, predictions, average="macro", zero_division=0)),
        labels=label_order,
        confusion_matrix=confusion_matrix(
            test_labels, predictions, labels=list(label_order)
        ).tolist(),
        classification_report=classification_report(
            test_labels,
            predictions,
            labels=list(label_order),
            output_dict=True,
            zero_division=0,
        ),
        test_size=len(test_labels),
    )
