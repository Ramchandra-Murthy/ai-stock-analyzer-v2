import pandas as pd
import pytest

from ai_trading.drawdown_periods import drawdown_periods


def test_drawdown_periods_reports_peak_valley_recovery_and_duration() -> None:
    index = pd.date_range("2026-01-01", periods=6, freq="D")
    returns = pd.Series([0.10, -0.05, -0.10, 0.20, -0.02, -0.03], index=index)

    report = drawdown_periods(returns, top=2)

    assert len(report) == 2
    assert report.loc[0, "drawdown"] == pytest.approx(-0.145)
    assert report.loc[0, "peak"] == index[0]
    assert report.loc[0, "valley"] == index[2]
    assert report.loc[0, "recovery"] == index[3]
    assert report.loc[0, "duration"] == 3
    assert pd.isna(report.loc[1, "recovery"])
    assert report.loc[1, "duration"] == 3


def test_drawdown_periods_handles_empty_returns() -> None:
    report = drawdown_periods(pd.Series(dtype=float))

    assert report.empty
    assert list(report.columns) == [
        "drawdown",
        "peak",
        "valley",
        "recovery",
        "duration",
    ]


def test_drawdown_periods_validates_top() -> None:
    with pytest.raises(ValueError, match="top must be at least 1"):
        drawdown_periods(pd.Series([0.01]), top=0)
