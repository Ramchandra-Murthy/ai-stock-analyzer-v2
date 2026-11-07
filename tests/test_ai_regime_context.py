"""Tests for AI market-regime context."""

import numpy as np
import pandas as pd

from ai_trading.regime_context import build_regime_context


def test_build_regime_context_returns_regime_fields() -> None:
    close = np.linspace(100.0, 160.0, 120)
    frame = pd.DataFrame(
        {
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
        }
    )

    result = build_regime_context(frame)

    assert result["regime"] in {"BULLISH", "BEARISH", "RANGE / MIXED", "INSUFFICIENT DATA"}
    assert isinstance(result["regime_score"], float)
    assert 0.0 <= float(result["regime_strength_pct"]) <= 100.0


def test_build_regime_context_handles_close_only_data() -> None:
    frame = pd.DataFrame({"Close": np.linspace(100.0, 140.0, 120)})

    result = build_regime_context(frame)

    assert result["regime"] in {"BULLISH", "BEARISH", "RANGE / MIXED", "INSUFFICIENT DATA"}
    assert isinstance(result["regime_score"], float)


def test_regime_context_adjusts_ohlc_for_corporate_actions() -> None:
    raw_close = np.array([100.0] * 100 + [50.0] * 20)
    factor = np.array([0.5] * 100 + [1.0] * 20)
    frame = pd.DataFrame(
        {
            "High": raw_close * 1.01,
            "Low": raw_close * 0.99,
            "Close": raw_close,
            "Adj Close": raw_close * factor,
        }
    )
    adjusted = pd.DataFrame(
        {
            "High": np.full(120, 50.5),
            "Low": np.full(120, 49.5),
            "Close": np.full(120, 50.0),
        }
    )

    assert build_regime_context(frame) == build_regime_context(adjusted)
