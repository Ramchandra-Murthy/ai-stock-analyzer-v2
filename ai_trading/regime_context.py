"""Market-regime context for AI trading signals."""

from __future__ import annotations

import pandas as pd

from engine.regime_engine import chapter4_regime


def build_regime_context(
    frame: pd.DataFrame,
    *,
    threshold: int = 3,
) -> dict[str, float | str]:
    """Return the latest multi-method regime snapshot for an OHLC frame."""
    if frame.empty or "Close" not in frame.columns:
        return {
            "regime": "INSUFFICIENT DATA",
            "regime_score": 0.0,
            "regime_strength_pct": 0.0,
        }

    required = {"High", "Low", "Close"}
    if not required.issubset(frame.columns):
        close = pd.to_numeric(frame["Close"], errors="coerce")
        frame = pd.DataFrame(
            {"High": close, "Low": close, "Close": close},
            index=frame.index,
        )

    result = chapter4_regime(frame, regime_threshold=threshold)
    if result.empty:
        return {
            "regime": "INSUFFICIENT DATA",
            "regime_score": 0.0,
            "regime_strength_pct": 0.0,
        }

    latest = result.iloc[-1]
    score = float(latest["regime_score"])
    strength = min(100.0, abs(score) / 7.0 * 100.0)
    return {
        "regime": str(latest["regime"]),
        "regime_score": score,
        "regime_strength_pct": round(strength, 1),
    }
