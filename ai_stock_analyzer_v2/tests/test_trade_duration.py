import pandas as pd
import pytest

from ai_trading.trade_duration import trade_duration_summary


def test_trade_duration_summary_reports_distribution() -> None:
    durations = pd.Series([1, 2, 3, 4, 10])

    report = trade_duration_summary(durations)

    assert report["trades"] == 5
    assert report["mean"] == pytest.approx(4.0)
    assert report["median"] == pytest.approx(3.0)
    assert report["minimum"] == pytest.approx(1.0)
    assert report["maximum"] == pytest.approx(10.0)
    assert report["p25"] == pytest.approx(2.0)
    assert report["p75"] == pytest.approx(4.0)


def test_trade_duration_summary_handles_empty_values() -> None:
    report = trade_duration_summary(pd.Series([1.0, None, float("nan")]))

    assert report["trades"] == 1
    assert report["median"] == pytest.approx(1.0)


def test_trade_duration_summary_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="durations must be non-negative"):
        trade_duration_summary(pd.Series([1.0, -1.0]))
