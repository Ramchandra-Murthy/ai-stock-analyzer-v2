import pandas as pd
import pytest

from ai_trading.sharpe_bootstrap import sharpe_bootstrap


def test_sharpe_bootstrap_returns_reproducible_interval() -> None:
    returns = pd.Series([0.01, -0.005, 0.02, 0.015, -0.002, 0.01])

    first = sharpe_bootstrap(returns, samples=50, seed=7)
    second = sharpe_bootstrap(returns, samples=50, seed=7)

    assert first == second
    assert first["observations"] == 6
    assert first["lower"] <= first["sharpe"] <= first["upper"]


def test_sharpe_bootstrap_handles_empty_returns() -> None:
    result = sharpe_bootstrap(pd.Series(dtype=float))

    assert result == {
        "observations": 0,
        "sharpe": None,
        "lower": None,
        "upper": None,
    }


def test_sharpe_bootstrap_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="samples must be at least 1"):
        sharpe_bootstrap(pd.Series([0.01, 0.02]), samples=0)

    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        sharpe_bootstrap(pd.Series([0.01, 0.02]), confidence=1.0)
