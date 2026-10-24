from datetime import date

from engine.nifty_options_v2_backtest import NiftyOptionsV2Backtest
from engine.nifty_options_v2_multiyear import MultiYearV2Runner, V2SeriesSpec
from strategy.nifty_options_v2 import NiftyCallContract, NiftyCallObservation


class FakeOptionsData:
    def get_observation(self, *, expiry: date, strike: float, observed_date: date):
        ltp = 100.0 if observed_date < expiry else 130.0
        return NiftyCallObservation(
            contract=NiftyCallContract(expiry=expiry, strike=strike),
            observed_date=observed_date,
            spot=15000.0,
            ltp=ltp,
        )


def test_multi_year_runner_accumulates_explicit_series() -> None:
    backtest = NiftyOptionsV2Backtest(FakeOptionsData())
    runner = MultiYearV2Runner(backtest)
    specs = [
        V2SeriesSpec(
            "2021-05",
            date(2021, 5, 27),
            14500,
            date(2021, 5, 27),
            date(2021, 5, 27),
        ),
        V2SeriesSpec(
            "2021-06",
            date(2021, 6, 24),
            14500,
            date(2021, 6, 24),
            date(2021, 6, 24),
        ),
    ]

    results = runner.run(specs)

    assert len(results) == 2
    assert runner.total_points(results) == 0.0
