from datetime import date

from engine.nifty_options_v2_auto import NiftyOptionsV2AutoPaper, PaperAction
from engine.nifty_options_v2_live import LivePaperObservation
from engine.nifty_options_v2_market_data import NiftyV2MarketObservation
from strategy.nifty_options_v2 import NiftyCallContract


def make_observation(
    *, observed_date: date, expiry: date, strike: float, ltp: float
) -> NiftyV2MarketObservation:
    return NiftyV2MarketObservation(
        contract=NiftyCallContract(expiry=expiry, strike=strike),
        observation=LivePaperObservation(observed_date=observed_date, spot=25000.0, ltp=ltp),
    )


def test_automatic_cycle_enters_then_exits_one_paper_trade() -> None:
    entry_expiry = date(2026, 10, 29)
    next_expiry = date(2026, 11, 26)
    auto = NiftyOptionsV2AutoPaper()

    entry = auto.process(
        observation=make_observation(
            observed_date=entry_expiry,
            expiry=next_expiry,
            strike=24500.0,
            ltp=600.0,
        ),
        current_series_expiry=entry_expiry,
    )
    assert entry.action is PaperAction.ENTER_NEXT_SERIES
    assert auto.session.trader.active_trade is not None
    assert auto.session.trader.active_trade.contract.expiry == next_expiry

    exit = auto.process(
        observation=make_observation(
            observed_date=next_expiry,
            expiry=next_expiry,
            strike=24500.0,
            ltp=650.0,
        ),
        current_series_expiry=next_expiry,
    )
    assert exit.action is PaperAction.EXIT_EXPIRY
    assert auto.session.trader.active_trade is None
    assert len(auto.session.trader.completed_trades) == 1
