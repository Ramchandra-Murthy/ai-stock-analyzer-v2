import pandas as pd
import pytest

from ai_trading.feature_drift import (
    build_feature_drift_report,
    compare_feature_drift,
)


def _frame(periods: int = 120, offset: float = 0.0) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=periods, freq="D")
    close = [100.0 + i * 0.5 + offset for i in range(periods)]
    volume = [1000.0 + i * 5 for i in range(periods)]
    return pd.DataFrame({"Close": close, "Volume": volume}, index=index)


def test_compare_feature_drift_flags_shifted_feature() -> None:
    baseline = pd.DataFrame({"return_1": [0.01] * 50})
    current = pd.DataFrame({"return_1": [0.08] * 50})
    report = compare_feature_drift(baseline, current, threshold=2.0)
    assert not report.empty
    assert report.iloc[0]["feature"] == "return_1"
    assert bool(report.iloc[0]["drifted"])


def test_build_feature_drift_report_from_ohlcv() -> None:
    report = build_feature_drift_report(_frame(), _frame(offset=50.0))
    assert not report.empty
    assert set(report["feature"]).issubset(
        {
            "return_1",
            "return_5",
            "return_20",
            "ema_gap",
            "volatility_20",
            "volume_ratio",
        }
    )


def test_invalid_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        compare_feature_drift(
            pd.DataFrame({"return_1": [0.01]}),
            pd.DataFrame({"return_1": [0.02]}),
            threshold=0.0,
        )
