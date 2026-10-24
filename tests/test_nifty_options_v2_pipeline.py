from datetime import date

import pytest

from engine.nifty_options_v2_backtest import NiftyOptionsV2Backtest
from engine.nifty_options_v2_pipeline import NiftyOptionsV2Pipeline, V2SeriesInput
from strategy.nifty_options_v2 import NiftyCallContract, NiftyCallObservation


def _observation(observed_date: date, spot: float, ltp: float) -> NiftyCallObservation:
    return NiftyCallObservation(
        NiftyCallContract(date(2021, 6, 24), 15000),
        observed_date,
        spot,
        ltp,
    )


class FakeData:
    rows = {
        date(2021, 5, 27): _observation(date(2021, 5, 27), 15300, 420),
        date(2021, 6, 24): _observation(date(2021, 6, 24), 15700, 760),
    }

    def get_observation(self, *, expiry, strike, observed_date):
        observation = self.rows[observed_date]
        return NiftyCallObservation(
            NiftyCallContract(observation.contract.expiry, strike),
            observation.observed_date,
            observation.spot,
            observation.ltp,
        )


def _pipeline() -> NiftyOptionsV2Pipeline:
    return NiftyOptionsV2Pipeline(NiftyOptionsV2Backtest(FakeData()))


def _series_input(strikes: list[float]) -> V2SeriesInput:
    return V2SeriesInput(
        series="2021-06",
        expiry=date(2021, 6, 24),
        entry_date=date(2021, 5, 27),
        exit_date=date(2021, 6, 24),
        spot_entry=15300,
        available_strikes=strikes,
    )


def test_pipeline_selects_strike_runs_trade_and_reports() -> None:
    trades, report = _pipeline().run([_series_input([14500, 15000, 15500])])

    assert len(trades) == 1
    assert trades[0].trade.entry.contract.strike == 14500
    assert report.total_points == 340
    assert report.winning_months == 1


def test_pipeline_rejects_when_no_itm_strike_exists() -> None:
    with pytest.raises(ValueError, match="no ITM"):
        _pipeline().run([_series_input([15300, 15500])])
