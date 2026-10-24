import pandas as pd

from algorithmic_trading.portfolio_allocation import (
    PortfolioLimits,
    allocate_scan,
    snapshot,
)


def test_allocate_scan_respects_position_cap() -> None:
    scan = pd.DataFrame(
        [
            {"symbol": "A", "signal": "LONG", "signal_score": 90.0},
            {"symbol": "B", "signal": "LONG", "signal_score": 80.0},
            {"symbol": "C", "signal": "FLAT", "signal_score": 70.0},
        ]
    )
    returns = pd.DataFrame(
        {
            "A": [0.01, -0.01, 0.02],
            "B": [0.02, -0.02, 0.01],
        }
    )

    result = allocate_scan(
        scan,
        returns,
        PortfolioLimits(max_position_weight=0.60, max_positions=2),
    )

    assert len(result) == 2
    assert result["target_weight"].abs().max() <= 0.60


def test_snapshot_rejects_excess_gross_exposure() -> None:
    index = pd.date_range("2026-01-01", periods=2)
    values = pd.DataFrame(
        {"A": [100.0, 150.0], "B": [100.0, 150.0]},
        index=index,
    )
    nav = pd.Series([200.0, 200.0], index=index)
    beta = pd.Series({"A": 1.0, "B": 1.0})

    result = snapshot(
        values,
        nav,
        beta,
        PortfolioLimits(max_gross_exposure=1.0),
    )

    assert result.gross == 1.5
    assert not result.allowed


def test_allocate_scan_hard_caps_four_short_positions_and_leaves_cash() -> None:
    scan = pd.DataFrame(
        [
            {"symbol": symbol, "signal": "SHORT", "signal_score": 90.0 - index}
            for index, symbol in enumerate(["A", "B", "C", "D"])
        ]
    )
    returns = pd.DataFrame({symbol: [0.01, -0.01, 0.02] for symbol in ["A", "B", "C", "D"]})

    result = allocate_scan(
        scan,
        returns,
        PortfolioLimits(max_position_weight=0.20, max_gross_exposure=1.0),
    )

    assert result["target_weight"].abs().max() <= 0.20 + 1e-12
    assert result["target_weight"].sum() == -0.80
    assert result["target_weight"].abs().sum() == 0.80
