import pandas as pd
import pytest

from ai_trading.factor_metrics import (
    daily_information_coefficient,
    factor_quantile_returns,
    factor_rank_autocorrelation,
    information_coefficient,
    quantile_turnover,
)


def test_information_coefficient_is_positive_for_matching_ranks():
    factor = pd.Series([1.0, 2.0, 3.0, 4.0])
    forward_returns = pd.Series([0.01, 0.02, 0.03, 0.04])

    assert information_coefficient(factor, forward_returns) == pytest.approx(1.0)


def test_information_coefficient_handles_constant_inputs():
    factor = pd.Series([1.0, 1.0, 1.0])
    forward_returns = pd.Series([0.01, 0.02, 0.03])

    assert information_coefficient(factor, forward_returns) == 0.0


def test_daily_information_coefficient_groups_by_date():
    data = pd.DataFrame(
        {
            "date": ["2026-01-01"] * 4 + ["2026-01-02"] * 4,
            "factor": [1, 2, 3, 4, 4, 3, 2, 1],
            "forward_return": [0.01, 0.02, 0.03, 0.04, 0.04, 0.03, 0.02, 0.01],
        }
    )

    result = daily_information_coefficient(
        data,
        date_column="date",
        factor_column="factor",
        forward_return_column="forward_return",
    )

    assert result.tolist() == pytest.approx([1.0, 1.0])


def test_factor_quantile_returns_preserves_low_to_high_quantile_order():
    data = pd.DataFrame(
        {
            "factor": [1, 2, 3, 4, 5, 6, 7, 8],
            "forward_return": [0.01, 0.01, 0.02, 0.02, 0.03, 0.03, 0.04, 0.04],
        }
    )

    result = factor_quantile_returns(
        data,
        factor_column="factor",
        forward_return_column="forward_return",
        quantiles=4,
    )

    assert result.tolist() == pytest.approx([0.01, 0.02, 0.03, 0.04])


def test_quantile_turnover_measures_membership_changes():
    previous = pd.Series({"A": 1, "B": 1, "C": 2, "D": 2})
    current = pd.Series({"A": 1, "B": 2, "C": 2, "D": 1})

    assert quantile_turnover(previous, current) == pytest.approx(0.5)


def test_factor_rank_autocorrelation_matches_rank_relationship():
    previous = pd.Series({"A": 1, "B": 2, "C": 3})
    current = pd.Series({"A": 2, "B": 4, "C": 6})

    assert factor_rank_autocorrelation(previous, current) == pytest.approx(1.0)


def test_factor_quantile_returns_rejects_too_few_quantiles():
    data = pd.DataFrame({"factor": [1, 2], "forward_return": [0.01, 0.02]})

    with pytest.raises(ValueError, match="at least 2"):
        factor_quantile_returns(
            data,
            factor_column="factor",
            forward_return_column="forward_return",
            quantiles=1,
        )
