from datetime import date

from engine.nifty_options_v2_backtest import NiftyOptionsV2Backtest
from engine.nifty_options_v2_monthly import MonthlyV2Runner
from strategy.nifty_options_v2 import NiftyCallContract, NiftyCallObservation


class FakeData:
    rows = {
        date(2021, 5, 27): NiftyCallObservation(
            NiftyCallContract(date(2021, 6, 24), 15000), date(2021, 5, 27), 15300, 420
        ),
        date(2021, 6, 24): NiftyCallObservation(
            NiftyCallContract(date(2021, 6, 24), 15000), date(2021, 6, 24), 15700, 760
        ),
    }

    def get_observation(self, *, expiry, strike, observed_date):
        return self.rows[observed_date]


def test_monthly_runner_runs_supplied_series() -> None:
    runner = MonthlyV2Runner(NiftyOptionsV2Backtest(FakeData()))
    results = runner.run(
        [("2021-06", date(2021, 6, 24), 15000, date(2021, 5, 27), date(2021, 6, 24))]
    )
    assert len(results) == 1
    assert results[0].series == "2021-06"
    assert results[0].points_pnl == 340
    assert runner.total_points(results) == 340


def test_monthly_runner_accepts_empty_schedule() -> None:
    runner = MonthlyV2Runner(NiftyOptionsV2Backtest(FakeData()))
    assert runner.run([]) == []
    assert runner.total_points([]) == 0
