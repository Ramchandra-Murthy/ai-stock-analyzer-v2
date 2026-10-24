import pandas as pd
import pytest

from ai_trading.parameter_sensitivity import (
    parameter_sensitivity_report,
    parameter_sensitivity_summary,
)


def test_parameter_sensitivity_report_ranks_configurations_by_return():
    returns = {
        "fast": pd.Series([0.02, -0.01, 0.03]),
        "slow": pd.Series([0.01, 0.01, 0.01]),
        "medium": pd.Series([-0.01, 0.02, 0.01]),
    }

    result = parameter_sensitivity_report(returns)

    assert result["parameter"].tolist() == ["fast", "slow", "medium"]
    assert result["return_rank"].tolist() == [1.0, 2.0, 3.0]


def test_parameter_sensitivity_report_ignores_invalid_observations():
    returns = {"config": pd.Series([0.01, None, 0.02])}

    result = parameter_sensitivity_report(returns)

    assert result["observations"].tolist() == [2.0]


def test_parameter_sensitivity_summary_reports_performance_spread():
    report = pd.DataFrame(
        {
            "parameter": ["a", "b", "c"],
            "total_return": [0.10, 0.05, -0.02],
            "sharpe_ratio": [1.5, 0.8, -0.4],
            "max_drawdown": [0.03, 0.05, 0.09],
        }
    )

    result = parameter_sensitivity_summary(report)

    assert result["configurations"] == 3.0
    assert result["best_parameter"] == "a"
    assert result["worst_parameter"] == "c"
    assert result["return_spread"] == pytest.approx(0.12)
    assert result["sharpe_spread"] == pytest.approx(1.9)
    assert result["drawdown_spread"] == pytest.approx(0.06)


def test_parameter_sensitivity_summary_handles_empty_report():
    report = pd.DataFrame(columns=["parameter", "total_return", "sharpe_ratio", "max_drawdown"])

    result = parameter_sensitivity_summary(report)

    assert result["configurations"] == 0.0
    assert result["best_parameter"] is None


def test_invalid_parameter_inputs_are_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        parameter_sensitivity_report({})

    with pytest.raises(ValueError, match="must be positive"):
        parameter_sensitivity_report({"config": pd.Series([0.01])}, periods_per_year=0)
