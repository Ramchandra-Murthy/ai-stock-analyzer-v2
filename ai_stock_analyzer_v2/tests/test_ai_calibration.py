"""Tests for AI model calibration and monitoring."""

import numpy as np
import pandas as pd
import pytest

from ai_trading.calibration import evaluate_calibration, monitor_calibration_frames


def _market_frame(rows: int = 180) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.02, rows)
    close = 100.0 * np.exp(np.cumsum(returns))
    return pd.DataFrame(
        {
            "Close": close,
            "Volume": rng.integers(900_000, 1_100_000, rows),
        }
    )


def test_calibration_returns_holdout_metrics_and_bins() -> None:
    metrics, summary = evaluate_calibration(
        _market_frame(),
        horizon=5,
        threshold=0.0,
        bins=5,
    )
    assert metrics.train_samples > metrics.test_samples
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.brier_score <= 1.0
    assert 0.0 <= metrics.calibration_gap <= 1.0
    assert metrics.test_samples == int(summary["samples"].sum())


def test_calibration_rejects_invalid_bin_count() -> None:
    with pytest.raises(ValueError, match="bins"):
        evaluate_calibration(_market_frame(), bins=1)


def test_multi_stock_calibration_monitor_returns_ranked_rows() -> None:
    result = monitor_calibration_frames(
        {"AAA": _market_frame(), "BBB": _market_frame(190)},
        threshold=0.0,
    )
    assert set(result["symbol"]) == {"AAA", "BBB"}
    assert list(result["calibration_gap_pct"]) == sorted(result["calibration_gap_pct"])
    assert (result["exchange"] == "NSE").all()


def test_multi_stock_calibration_rejects_invalid_exchange() -> None:
    with pytest.raises(ValueError, match="exchange"):
        monitor_calibration_frames({"AAA": _market_frame()}, exchange="NYSE")
