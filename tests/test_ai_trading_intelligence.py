"""Tests for the AI trading intelligence baseline."""

import pandas as pd

from ai_trading.features import build_features
from ai_trading.ml_model import make_training_dataset
from ai_trading.signal_engine import score_features


def test_build_features_contains_model_inputs() -> None:
    frame = pd.DataFrame(
        {
            "Close": [100.0 + i for i in range(60)],
            "Volume": [1_000_000.0 + i * 1000 for i in range(60)],
        }
    )
    features = build_features(frame)
    assert {"return_5", "return_20", "ema_gap", "volatility_20", "volume_ratio"}.issubset(
        features.columns
    )
    assert not features.empty


def test_signal_engine_returns_expected_columns() -> None:
    frame = pd.DataFrame(
        {
            "return_5": [0.04],
            "return_20": [0.08],
            "ema_gap": [0.03],
            "volatility_20": [0.02],
            "volume_ratio": [1.4],
        }
    )
    result = score_features(frame)
    assert list(result.columns) == ["score", "confidence", "signal"]
    assert result.iloc[0]["signal"] == "LONG"
    assert 0.0 <= result.iloc[0]["confidence"] <= 1.0


def test_ml_labels_use_adjusted_close_across_stock_split() -> None:
    index = pd.date_range("2026-01-01", periods=80, freq="B")
    adjusted = pd.Series([100.0 + i for i in range(80)], index=index)
    raw = adjusted.copy()
    raw.loc[index[40]:] = raw.loc[index[40]:] / 2.0
    frame = pd.DataFrame(
        {
            "Open": raw,
            "High": raw * 1.01,
            "Low": raw * 0.99,
            "Close": raw,
            "Adj Close": adjusted,
            "Volume": 1_000_000.0,
        },
        index=index,
    )

    features, labels = make_training_dataset(frame, horizon=5, threshold=0.01)

    assert index[35] in features.index
    assert labels.loc[index[35]] == 1
