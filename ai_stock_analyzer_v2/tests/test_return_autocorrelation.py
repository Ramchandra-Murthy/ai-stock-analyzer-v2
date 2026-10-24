import pandas as pd
import pytest

from ai_trading.return_autocorrelation import (
    return_autocorrelation,
    return_autocorrelation_summary,
)


def test_return_autocorrelation_matches_lagged_correlation() -> None:
    returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])

    assert return_autocorrelation(returns, lag=1) == pytest.approx(1.0)


def test_return_autocorrelation_returns_none_when_insufficient_history() -> None:
    returns = pd.Series([0.01, 0.02])

    assert return_autocorrelation(returns, lag=2) is None


def test_return_autocorrelation_summary_reports_selected_lags() -> None:
    returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])

    report = return_autocorrelation_summary(returns, lags=(1, 2))

    assert set(report) == {"lag_1", "lag_2"}
    assert report["lag_1"] == pytest.approx(1.0)


def test_return_autocorrelation_rejects_invalid_lag() -> None:
    with pytest.raises(ValueError, match="lag must be at least 1"):
        return_autocorrelation(pd.Series([0.01, 0.02]), lag=0)
