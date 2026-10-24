"""Model-free baseline signal engine for AI trading research.

This first implementation creates a deterministic probability-like score from
engineered features. It is intentionally labelled as a baseline until a
trained, validated ML model is introduced.
"""

from __future__ import annotations

import pandas as pd


def score_features(features: pd.DataFrame) -> pd.DataFrame:
    """Return directional score and confidence from normalized features."""
    if features.empty:
        return pd.DataFrame(columns=["score", "confidence", "signal"])

    score = (
        features["return_5"].clip(-0.05, 0.05) * 8.0
        + features["return_20"].clip(-0.15, 0.15) * 3.0
        + features["ema_gap"].clip(-0.10, 0.10) * 5.0
        + (features["volume_ratio"].clip(0.5, 2.0) - 1.0) * 0.5
    )
    score = score.clip(-1.0, 1.0)
    confidence = (0.5 + 0.5 * score.abs()).clip(0.0, 1.0)
    signal = pd.Series("NEUTRAL", index=features.index)
    signal.loc[score >= 0.25] = "LONG"
    signal.loc[score <= -0.25] = "SHORT"

    return pd.DataFrame(
        {"score": score, "confidence": confidence, "signal": signal},
        index=features.index,
    )
