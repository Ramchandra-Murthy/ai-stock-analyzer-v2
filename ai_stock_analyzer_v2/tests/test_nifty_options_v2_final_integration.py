from datetime import date

from engine.nifty_options_v2_auto import NiftyOptionsV2AutoPaper, PaperAction
from engine.nifty_options_v2_auto_cycle import NiftyOptionsV2AutoCycle
from engine.nifty_options_v2_live import LivePaperObservation
from engine.nifty_options_v2_market_data import NiftyV2MarketObservation
from engine.nifty_options_v2_paper_report import build_paper_session_report
from engine.nifty_options_v2_readiness import automatic_cycle_ready
from strategy.nifty_options_v2 import NiftyCallContract


def observation(observed_date: date, expiry: date, ltp: float) -> NiftyV2MarketObservation:
    return NiftyV2MarketObservation(
        contract=NiftyCallContract(expiry=expiry, strike=24500.0),
        observation=LivePaperObservation(observed_date=observed_date, spot=25000.0, ltp=ltp),
    )


def test_final_nifty_v2_paper_flow_is_ready_and_reports_completed_trade() -> None:
    assert automatic_cycle_ready(
        provider_ready=True,
        market_session_ready=True,
        market_data_fresh=True,
    ).ready

    auto = NiftyOptionsV2AutoCycle(auto_paper=NiftyOptionsV2AutoPaper())
    expiries = ("2026-10-29", "2026-11-26")

    entry = auto.process(
        expiries=expiries,
        observed_date=date(2026, 10, 29),
        observation=observation(date(2026, 10, 29), date(2026, 11, 26), 600.0),
    )
    assert entry is not None
    assert entry.action is PaperAction.ENTER_NEXT_SERIES

    exit_result = auto.process(
        expiries=expiries,
        observed_date=date(2026, 11, 26),
        observation=observation(date(2026, 11, 26), date(2026, 11, 26), 650.0),
    )
    assert exit_result is not None
    assert exit_result.action is PaperAction.EXIT_EXPIRY

    report = build_paper_session_report(auto.auto_paper.session.trader.completed_trades)
    assert report.completed_trades == 1
    assert report.winning_trades == 1
    assert report.total_points == 50.0
