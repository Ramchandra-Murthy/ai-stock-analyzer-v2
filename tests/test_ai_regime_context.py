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
