import pandas as pd
import pytest

from ai_trading.rolling_risk import rolling_risk_metrics


def test_rolling_risk_metrics_builds_consecutive_windows():
    returns = pd.Series([0.01, -0.02, 0.03, 0.01])

    result = rolling_risk_metrics(returns, window=3)

    assert result["end"].tolist() == [2, 3]
    assert len(result) == 2
    assert result["annualized_volatility"].notna().all()
    assert result["sharpe_ratio"].notna().all()
    assert result["max_drawdown"].notna().all()


def test_rolling_risk_metrics_drops_invalid_observations():
    returns = pd.Series([0.01, None, -0.02, 0.03])

    result = rolling_risk_metrics(returns, window=3)

    assert len(result) == 1


def test_rolling_risk_metrics_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="at least 2"):
        rolling_risk_metrics(pd.Series([0.01, 0.02]), window=1)

    with pytest.raises(ValueError, match="must be positive"):
        rolling_risk_metrics(pd.Series([0.01, 0.02]), window=2, periods_per_year=0)

    with pytest.raises(ValueError, match="not enough observations"):
        rolling_risk_metrics(pd.Series([0.01]), window=2)
