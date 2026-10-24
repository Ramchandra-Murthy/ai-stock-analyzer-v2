import math

import pandas as pd
import pytest

from ai_trading.multiple_testing import (
    multiple_testing_summary,
    sharpe_ratio_haircut,
)


def test_sharpe_ratio_haircut_penalizes_multiple_trials():
    ratios = pd.Series([0.8, 1.2, 1.0])

    result = sharpe_ratio_haircut(ratios, trials=3)

    assert result == pytest.approx(1.2 - math.sqrt(2.0 * math.log(3)))


def test_sharpe_ratio_haircut_returns_best_for_single_trial():
    ratios = pd.Series([0.8, 1.2, 1.0])

    assert sharpe_ratio_haircut(ratios, trials=1) == pytest.approx(1.2)


def test_sharpe_ratio_haircut_drops_invalid_values():
    ratios = pd.Series([0.8, None, 1.2])

    assert sharpe_ratio_haircut(ratios, trials=1) == pytest.approx(1.2)


def test_multiple_testing_summary_reports_adjusted_result():
    ratios = pd.Series([0.5, 1.0, 0.7])

    result = multiple_testing_summary(ratios, trials=3)

    assert result["configurations"] == 3.0
    assert result["best_sharpe"] == pytest.approx(1.0)
    assert result["adjusted_sharpe"] is not None


def test_multiple_testing_summary_handles_empty_input():
    result = multiple_testing_summary(pd.Series(dtype=float), trials=2)

    assert result["configurations"] == 0.0
    assert result["best_sharpe"] is None
    assert result["adjusted_sharpe"] is None


def test_invalid_trial_count_is_rejected():
    with pytest.raises(ValueError, match="at least 1"):
        sharpe_ratio_haircut(pd.Series([1.0]), trials=0)
