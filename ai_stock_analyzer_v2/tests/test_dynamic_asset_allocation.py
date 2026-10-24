import pandas as pd
import pytest

from algorithmic_trading.dynamic_asset_allocation import (
    DynamicAllocationConfig,
    dynamic_asset_allocation,
    latest_dynamic_allocation,
)


def test_dynamic_allocation_scales_exposure_after_drawdown() -> None:
    returns = pd.DataFrame(
        {
            "RELIANCE": [0.01, -0.01, 0.01],
            "TCS": [0.02, -0.02, 0.02],
        }
    )
    equity = pd.Series(
        [100.0, 90.0, 91.0],
        index=pd.date_range("2026-01-01", periods=3),
    )

    allocation = dynamic_asset_allocation(
        returns,
        equity,
        DynamicAllocationConfig(
            max_drawdown_tolerance=-0.10,
            min_risk=0.25,
            max_risk=1.0,
            smoothing_span=2,
            max_weight=0.50,
        ),
    )

    assert list(allocation.columns) == ["RELIANCE", "TCS"]
    assert float(allocation.iloc[0].sum()) <= 1.0
    assert float(allocation.iloc[1].sum()) < float(allocation.iloc[0].sum())


def test_latest_dynamic_allocation_supports_inverse_volatility() -> None:
    returns = pd.DataFrame(
        {
            "RELIANCE": [0.01, 0.01, 0.01, 0.01],
            "TCS": [0.02, -0.02, 0.02, -0.02],
        }
    )
    equity = pd.Series(
        [100.0, 101.0, 100.5, 101.0],
        index=pd.date_range("2026-01-01", periods=4),
    )

    result = latest_dynamic_allocation(
        returns,
        equity,
        DynamicAllocationConfig(
            method="inverse_volatility",
            max_weight=0.80,
        ),
    )

    assert set(result.index) == {"RELIANCE", "TCS"}
    assert float(result.sum()) <= 1.0
    assert result["RELIANCE"] > result["TCS"]


def test_dynamic_allocation_rejects_invalid_method() -> None:
    returns = pd.DataFrame({"A": [0.01, 0.02]})
    equity = pd.Series([100.0, 101.0])

    with pytest.raises(ValueError, match="unsupported allocation method"):
        dynamic_asset_allocation(
            returns,
            equity,
            DynamicAllocationConfig(method="max_sharpe"),
        )
