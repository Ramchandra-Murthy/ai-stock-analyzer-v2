from datetime import date

from engine.nifty_options_v2_auto import PaperAction
from engine.nifty_options_v2_auto_cycle import NiftyOptionsV2AutoCycle
from engine.nifty_options_v2_live import LivePaperObservation
from engine.nifty_options_v2_market_data import NiftyV2MarketObservation
from strategy.nifty_options_v2 import NiftyCallContract


def test_dashboard_cycle_uses_next_month_contract_for_entry() -> None:
    coordinator = NiftyOptionsV2AutoCycle()

    observation = NiftyV2MarketObservation(
        contract=NiftyCallContract(expiry=date(2026, 11, 26), strike=24000),
        observation=LivePaperObservation(
            observed_date=date(2026, 10, 29),
            spot=25000,
            ltp=1000,
        ),
    )

    result = coordinator.process(
        expiries=("2026-10-29", "2026-11-26"),
        observed_date=date(2026, 10, 29),
        observation=observation,
    )

    assert result is not None
    assert result.action is PaperAction.ENTER_NEXT_SERIES
    assert result.next_expiry == date(2026, 11, 26)
    assert coordinator.auto_paper.session.trader.active_trade is not None
    assert coordinator.auto_paper.session.trader.active_trade.contract.expiry == date(2026, 11, 26)
