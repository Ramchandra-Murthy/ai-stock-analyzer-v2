from datetime import date

from engine.nifty_options_v2_paper import PaperTrade
from engine.nifty_options_v2_paper_report import build_paper_session_report
from strategy.nifty_options_v2 import NiftyCallContract


def make_trade(entry: float, exit: float) -> PaperTrade:
    return PaperTrade(
        contract=NiftyCallContract(expiry=date(2026, 10, 29), strike=24500.0),
        entry_date=date(2026, 10, 1),
        entry_ltp=entry,
        exit_date=date(2026, 10, 29),
        exit_ltp=exit,
    )


def test_paper_session_report_counts_results_and_drawdown() -> None:
    report = build_paper_session_report(
        [
            make_trade(500.0, 600.0),
            make_trade(600.0, 550.0),
            make_trade(550.0, 650.0),
        ]
    )

    assert report.completed_trades == 3
    assert report.winning_trades == 2
    assert report.losing_trades == 1
    assert report.total_points == 150.0
    assert report.max_drawdown_points == 50.0


def test_paper_session_report_ignores_unclosed_trades() -> None:
    trade = PaperTrade(
        contract=NiftyCallContract(expiry=date(2026, 10, 29), strike=24500.0),
        entry_date=date(2026, 10, 1),
        entry_ltp=500.0,
    )

    report = build_paper_session_report([trade])

    assert report.completed_trades == 0
    assert report.total_points == 0.0
