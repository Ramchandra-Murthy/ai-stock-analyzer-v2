from datetime import date

import pytest

from engine.nifty_options_v2_backtest import NiftyOptionsV2Backtest
from strategy.nifty_options_v2 import NiftyCallContract, NiftyCallObservation


class FakeHistoricalData:
    def __init__(self) -> None:
        self.rows = {
            date(2021, 5, 27): NiftyCallObservation(
                NiftyCallContract(date(2021, 6, 24), 15000), date(2021, 5, 27), 15300, 420
            ),
            date(2021, 6, 24): NiftyCallObservation(
                NiftyCallContract(date(2021, 6, 24), 15000), date(2021, 6, 24), 15700, 760
            ),
        }

    def get_observation(self, *, expiry, strike, observed_date):
        return self.rows[observed_date]


def test_v2_backtest_holds_call_until_exit() -> None:
    trade = NiftyOptionsV2Backtest(FakeHistoricalData()).run_trade(
        expiry=date(2021, 6, 24),
        strike=15000,
        entry_date=date(2021, 5, 27),
        exit_date=date(2021, 6, 24),
    )
    assert trade.points_pnl == 340
    assert trade.gross_pnl == 340


def test_v2_backtest_rejects_non_itm_entry() -> None:
    class NonItm(FakeHistoricalData):
        def get_observation(self, **kwargs):
            return NiftyCallObservation(
                NiftyCallContract(date(2021, 6, 24), 16000),
                kwargs["observed_date"],
                15300,
                420,
            )

    with pytest.raises(ValueError, match="ITM CALL"):
        NiftyOptionsV2Backtest(NonItm()).run_trade(
            expiry=date(2021, 6, 24),
            strike=16000,
            entry_date=date(2021, 5, 27),
            exit_date=date(2021, 6, 24),
        )


def test_v2_backtest_rejects_reverse_dates() -> None:
    with pytest.raises(ValueError, match="exit_date"):
        NiftyOptionsV2Backtest(FakeHistoricalData()).run_trade(
            expiry=date(2021, 6, 24),
            strike=15000,
            entry_date=date(2021, 6, 24),
            exit_date=date(2021, 5, 27),
        )
