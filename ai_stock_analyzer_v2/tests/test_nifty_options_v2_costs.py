import pytest

from engine.nifty_options_v2_costs import (
    V2CostModel,
    capital_return,
    max_drawdown,
    net_pnl,
    net_points,
)


def test_net_points_and_pnl_apply_costs_and_slippage() -> None:
    costs = V2CostModel(entry_cost=20, exit_cost=30, slippage_points=2)

    assert net_points(100, lot_size=50, costs=costs) == pytest.approx(97.0)
    assert net_pnl(100, lot_size=50, costs=costs) == pytest.approx(4850.0)


def test_cost_model_rejects_negative_assumptions() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        V2CostModel(entry_cost=-1)


def test_max_drawdown_returns_peak_to_trough_amount() -> None:
    assert max_drawdown([100, 160, 120, 190, 80]) == 110


def test_capital_return() -> None:
    assert capital_return(25000, 250000) == pytest.approx(0.10)
