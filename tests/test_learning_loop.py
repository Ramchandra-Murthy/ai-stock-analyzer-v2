import pandas as pd
import pytest

from ai_trading.learning_loop import learning_loop_summary, run_learning_loop


def _history() -> pd.DataFrame:
    rows = []
    for index in range(12):
        rows.append(
            {
                "timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(days=index),
                "symbol": "ABC",
                "signal": "LONG",
                "regime": "BULLISH",
                "confidence_pct": 70.0,
                "completed": index < 11,
                "return_pct": 2.0 if index < 10 else -1.0,
            }
        )
    return pd.DataFrame(rows)


def test_learning_loop_does_not_use_future_outcomes() -> None:
    replay = run_learning_loop(_history(), min_samples=10)

    assert replay.iloc[0]["adaptive_confidence_pct"] == pytest.approx(70.0)
    assert replay.iloc[10]["adaptive_adjustment_pct"] == pytest.approx(10.0)
    assert replay.iloc[11]["adaptive_confidence_pct"] == pytest.approx(80.0)
    assert replay.iloc[11]["learning_samples"] == 11


def test_learning_loop_summary_is_bounded() -> None:
    summary = learning_loop_summary(
        run_learning_loop(_history(), min_samples=10, max_adjustment_pct=5.0)
    )

    assert summary["signals"] == 12.0
    assert summary["completed"] == 11.0
    assert summary["maximum_adjustment_pct"] <= 5.0


def test_empty_learning_loop() -> None:
    replay = run_learning_loop(pd.DataFrame())
    assert replay.empty
    assert learning_loop_summary(replay)["signals"] == 0.0


def test_learning_loop_does_not_use_same_timestamp_outcomes() -> None:
    timestamp = pd.Timestamp("2026-01-01")
    history = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "symbol": "AAA",
                "signal": "LONG",
                "regime": "BULLISH",
                "confidence_pct": 70.0,
                "completed": True,
                "return_pct": 2.0,
            },
            {
                "timestamp": timestamp,
                "symbol": "BBB",
                "signal": "LONG",
                "regime": "BULLISH",
                "confidence_pct": 70.0,
                "completed": False,
                "return_pct": None,
            },
            {
                "timestamp": timestamp + pd.Timedelta(days=1),
                "symbol": "CCC",
                "signal": "LONG",
                "regime": "BULLISH",
                "confidence_pct": 70.0,
                "completed": False,
                "return_pct": None,
            },
        ]
    )

    replay = run_learning_loop(history, min_samples=1)

    assert replay.iloc[1]["adaptive_adjustment_pct"] == pytest.approx(0.0)
    assert replay.iloc[2]["adaptive_adjustment_pct"] == pytest.approx(10.0)


def test_learning_loop_reports_samples_from_exact_regime_match() -> None:
    timestamp = pd.Timestamp("2026-01-01")
    rows = [
        {
            "timestamp": timestamp,
            "symbol": f"ALL{i}",
            "signal": "LONG",
            "regime": "ALL",
            "confidence_pct": 70.0,
            "completed": True,
            "return_pct": -1.0,
        }
        for i in range(12)
    ]
    rows.extend(
        {
            "timestamp": timestamp,
            "symbol": f"BULL{i}",
            "signal": "LONG",
            "regime": "BULLISH",
            "confidence_pct": 70.0,
            "completed": True,
            "return_pct": 2.0,
        }
        for i in range(10)
    )
    rows.append(
        {
            "timestamp": timestamp + pd.Timedelta(days=1),
            "symbol": "NEXT",
            "signal": "LONG",
            "regime": "BULLISH",
            "confidence_pct": 70.0,
            "completed": False,
            "return_pct": None,
        }
    )

    replay = run_learning_loop(pd.DataFrame(rows), min_samples=10)

    assert replay.iloc[-1]["learning_samples"] == 10
    assert replay.iloc[-1]["adaptive_adjustment_pct"] == pytest.approx(10.0)
