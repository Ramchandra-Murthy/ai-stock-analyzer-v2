import math
from datetime import date

import pytest

from engine.nifty_options_v2_paper import NiftyOptionsV2PaperTrader
from strategy.nifty_options_v2 import NiftyCallContract


def test_paper_trade_records_entry_and_exit() -> None:
    trader = NiftyOptionsV2PaperTrader()
    contract = NiftyCallContract(expiry=date(2026, 10, 29), strike=24000)

    trader.enter(
        contract=contract,
        observed_date=date(2026, 10, 1),
        spot=25000,
        ltp=1000,
    )
    closed = trader.mark_exit(observed_date=date(2026, 10, 29), ltp=1200)

    assert closed.points_pnl == 200
    assert trader.active_trade is None
    assert trader.completed_trades == [closed]


def test_paper_entry_requires_itm_call() -> None:
    trader = NiftyOptionsV2PaperTrader()
    contract = NiftyCallContract(expiry=date(2026, 10, 29), strike=25000)

    with pytest.raises(ValueError, match="ITM CALL"):
        trader.enter(
            contract=contract,
            observed_date=date(2026, 10, 1),
            spot=25000,
            ltp=1000,
        )


def test_paper_trader_allows_only_one_active_trade() -> None:
    trader = NiftyOptionsV2PaperTrader()
    contract = NiftyCallContract(expiry=date(2026, 10, 29), strike=24000)
    trader.enter(
        contract=contract,
        observed_date=date(2026, 10, 1),
        spot=25000,
        ltp=1000,
    )

    with pytest.raises(ValueError, match="already active"):
        trader.enter(
            contract=contract,
            observed_date=date(2026, 10, 2),
            spot=25100,
            ltp=1050,
        )


@pytest.mark.parametrize(
    ("spot", "ltp", "message"),
    [
        (0, 1000, "spot must be finite and positive"),
        (math.nan, 1000, "spot must be finite and positive"),
        (25000, math.nan, "ltp must be finite and non-negative"),
        (25000, math.inf, "ltp must be finite and non-negative"),
    ],
)
def test_paper_entry_rejects_invalid_observation_values(
    spot: float,
    ltp: float,
    message: str,
) -> None:
    trader = NiftyOptionsV2PaperTrader()
    contract = NiftyCallContract(expiry=date(2026, 10, 29), strike=24000)

    with pytest.raises(ValueError, match=message):
        trader.enter(
            contract=contract,
            observed_date=date(2026, 10, 1),
            spot=spot,
            ltp=ltp,
        )


def test_paper_entry_requires_future_expiry() -> None:
    trader = NiftyOptionsV2PaperTrader()
    contract = NiftyCallContract(expiry=date(2026, 10, 8), strike=24000)

    with pytest.raises(ValueError, match="before contract expiry"):
        trader.enter(
            contract=contract,
            observed_date=date(2026, 10, 8),
            spot=25000,
            ltp=1000,
        )
