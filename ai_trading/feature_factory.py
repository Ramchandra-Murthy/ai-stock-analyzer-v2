"""Standardized leakage-safe feature factory for AI trading research."""

from __future__ import annotations

import pandas as pd

from ai_trading.features import build_features
from ai_trading.fundamental_intelligence import FundamentalSnapshot


def build_ai_feature_frame(
    frame: pd.DataFrame,
    *,
    fundamentals: FundamentalSnapshot | None = None,
    sentiment_score: float | None = None,
) -> pd.DataFrame:
    """Build one standardized feature frame from market and research inputs."""
    if frame.empty:
        return pd.DataFrame()

    features = build_features(frame).copy()

    if fundamentals is not None:
        features["fundamental_revenue_growth_pct"] = fundamentals.revenue_growth_pct
        features["fundamental_earnings_growth_pct"] = fundamentals.earnings_growth_pct
        features["fundamental_profit_margin_pct"] = fundamentals.profit_margin_pct
        features["fundamental_debt_to_equity"] = fundamentals.debt_to_equity
        features["fundamental_roe_pct"] = fundamentals.return_on_equity_pct
        features["fundamental_pe_ratio"] = fundamentals.pe_ratio

    features["news_sentiment_score"] = (
        float(sentiment_score) if sentiment_score is not None else 0.0
    )
    return features.replace([float("inf"), float("-inf")], pd.NA)


def latest_ai_features(
    frame: pd.DataFrame,
    *,
    fundamentals: FundamentalSnapshot | None = None,
    sentiment_score: float | None = None,
) -> pd.Series:
    """Return the latest standardized AI feature vector."""
    features = build_ai_feature_frame(
        frame,
        fundamentals=fundamentals,
        sentiment_score=sentiment_score,
    )
    if features.empty:
        return pd.Series(dtype=float)
    return features.iloc[-1]
