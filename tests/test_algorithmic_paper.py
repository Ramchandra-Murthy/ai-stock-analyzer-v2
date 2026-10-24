import pandas as pd
import pytest

from algorithmic_trading.algorithmic_paper import rebalance_from_scan
from algorithmic_trading.paper_trading import PaperPortfolio


def test_rebalance_applies_long_target() -> None:
    portfolio = PaperPortfolio(cash=10_000.0)
    scan = pd.DataFrame(
        [
            {
                "symbol": "RELIANCE",
                "price": 100.0,
                "signal": "LONG",
                "quantity": 20,
            }
        ]
    )

    result = rebalance_from_scan(portfolio, scan)

    assert portfolio.positions == {"RELIANCE": 20}
    assert result.equity == 10_000.0
    assert len(result.fills) == 1


def test_rebalance_can_move_to_short_target() -> None:
    portfolio = PaperPortfolio(cash=10_000.0)
    portfolio.positions["TCS"] = 10
    scan = pd.DataFrame(
        [
            {
                "symbol": "TCS",
                "price": 200.0,
                "signal": "SHORT",
                "quantity": 10,
            }
        ]
    )

    result = rebalance_from_scan(portfolio, scan)

    assert portfolio.positions == {"TCS": -10}
    assert result.reconciliation[0].status.value == "matched"


def test_rebalance_requires_scan_columns() -> None:
    with pytest.raises(ValueError, match="missing required"):
        rebalance_from_scan(PaperPortfolio(cash=10_000.0), pd.DataFrame())
