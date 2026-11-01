"""Stock sentiment research module (text scoring, aggregation, evaluation).

Research use only. Nothing here places orders or constitutes investment advice.
"""

from sentiment.aggregate import (
    daily_sentiment,
    decayed_sentiment,
    sentiment_features,
    sentiment_signal,
)
from sentiment.evaluation import information_coefficient, quantile_forward_returns
from sentiment.scorer import TextSentiment, score_articles, score_text

__all__ = [
    "TextSentiment",
    "daily_sentiment",
    "decayed_sentiment",
    "information_coefficient",
    "quantile_forward_returns",
    "score_articles",
    "score_text",
    "sentiment_features",
    "sentiment_signal",
]
