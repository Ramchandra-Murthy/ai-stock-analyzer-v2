import numpy as np
import pandas as pd
import pytest

from engine.trading_pipeline import integrated_trade_frame, integrated_trade_snapshot


def _prices(rows: int = 60) -> pd.DataFrame:
    close = np.linspace(100.0, 130.0, rows)
    return pd.DataFrame(
        {
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
        },
        index=pd.date_range("2026-01-01", periods=rows, freq="D"),
    )


def test_integrated_trade_snapshot_connects_chapter_modules() -> None:
    result = integrated_trade_snapshot(
        _prices(),
        capital=100_000.0,
        risk_fraction=0.01,
        stop_price=125.0,
        equity_curve=pd.Series([100_000.0, 101_000.0, 100_500.0]),
        journal_score=95.0,
        fast_period=5,
        slow_period=20,
    )

    assert result["regime"] in {"BULLISH", "BEARISH", "RANGE / MIXED", "INSUFFICIENT DATA"}
    assert result["edge_signal"] == 1.0
    assert result["direction"] == "LONG"
    assert result["risk_appetite"] >= 0.25
    assert result["adjusted_position_size"] > 0
    assert result["journal_score"] == 95.0


def test_integrated_trade_frame_is_dashboard_ready() -> None:
    result = integrated_trade_frame(_prices(), fast_period=5, slow_period=20)

    assert list(result.columns) == [
        "close",
        "edge_signal",
        "regime_score",
        "regime",
    ]
    assert len(result) == 60
    assert result["edge_signal"].iloc[-1] == 1.0


def test_integration_validates_empty_and_short_data() -> None:
    with pytest.raises(ValueError, match="prices must not be empty"):
        integrated_trade_snapshot(
            pd.DataFrame(),
            capital=100_000,
            risk_fraction=0.01,
            stop_price=95,
            equity_curve=pd.Series([100_000]),
        )

    with pytest.raises(ValueError, match="enough bars"):
        integrated_trade_frame(_prices(10), fast_period=5, slow_period=20)
