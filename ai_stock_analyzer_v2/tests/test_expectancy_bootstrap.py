import pandas as pd
import pytest

from ai_trading.expectancy_bootstrap import expectancy_bootstrap


def test_expectancy_bootstrap_reports_interval() -> None:
    returns = pd.Series([2.0, 3.0, -1.0, -1.0])

    report = expectancy_bootstrap(returns, samples=200, confidence=0.90)

    assert report["trades"] == 4
    assert report["expectancy"] == pytest.approx(0.75)
    assert report["lower"] <= report["expectancy"] <= report["upper"]


def test_expectancy_bootstrap_handles_empty_returns() -> None:
    report = expectancy_bootstrap(pd.Series(dtype=float))

    assert report == {
        "trades": 0,
        "expectancy": None,
        "lower": None,
        "upper": None,
    }


def test_expectancy_bootstrap_validates_arguments() -> None:
    with pytest.raises(ValueError, match="samples must be at least 1"):
        expectancy_bootstrap(pd.Series([1.0]), samples=0)

    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        expectancy_bootstrap(pd.Series([1.0]), confidence=1.0)
