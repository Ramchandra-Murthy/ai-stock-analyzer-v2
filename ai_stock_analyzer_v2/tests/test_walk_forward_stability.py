import pandas as pd
import pytest

from ai_trading.walk_forward_stability import (
    stability_summary,
    walk_forward_window_metrics,
)


def test_walk_forward_window_metrics_splits_returns_into_consecutive_windows():
    returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.02, 0.01])

    result = walk_forward_window_metrics(returns, window_size=3)

    assert result["window"].tolist() == [1, 2]
    assert result["total_return"].tolist() == pytest.approx(
        [(1.01 * 1.02 * 0.99) - 1.0, (1.03 * 0.98 * 1.01) - 1.0]
    )


def test_walk_forward_window_metrics_reports_win_rate_and_drawdown():
    returns = pd.Series([0.10, -0.05, 0.02, -0.01])

    result = walk_forward_window_metrics(returns, window_size=2)

    assert result["win_rate"].tolist() == pytest.approx([0.5, 0.5])
    assert result["max_drawdown"].iloc[0] == pytest.approx(0.05)


def test_walk_forward_window_metrics_drops_invalid_returns():
    returns = pd.Series([0.01, None, 0.02, 0.03])

    result = walk_forward_window_metrics(returns, window_size=3)

    assert len(result) == 1


def test_stability_summary_reports_dispersion_across_windows():
    metrics = pd.DataFrame(
        {
            "total_return": [0.05, 0.02, -0.01],
            "win_rate": [0.6, 0.5, 0.4],
            "sharpe_ratio": [1.2, 0.8, -0.2],
            "max_drawdown": [0.03, 0.05, 0.08],
        }
    )

    result = stability_summary(metrics)

    assert result["windows"] == 3.0
    assert result["return_mean"] == pytest.approx(0.02)
    assert result["max_drawdown_worst"] == pytest.approx(0.08)


def test_stability_summary_handles_empty_metrics():
    metrics = pd.DataFrame(columns=["total_return", "win_rate", "sharpe_ratio", "max_drawdown"])

    result = stability_summary(metrics)

    assert result["windows"] == 0.0
    assert result["return_mean"] is None


def test_invalid_window_size_is_rejected():
    with pytest.raises(ValueError, match="at least 2"):
        walk_forward_window_metrics(pd.Series([0.01, 0.02]), window_size=1)
