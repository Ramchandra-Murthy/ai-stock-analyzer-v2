from dataclasses import dataclass

from engine.nifty_options_v2_report import build_report


@dataclass(frozen=True)
class Result:
    points_pnl: float


def test_build_report_calculates_core_metrics() -> None:
    report = build_report([Result(100), Result(-40), Result(20), Result(-90)])
    assert report.total_points == -10
    assert report.winning_months == 2
    assert report.losing_months == 2
    assert report.win_rate == 0.5
    assert report.max_drawdown_points == 110


def test_build_report_handles_empty_results() -> None:
    report = build_report([])
    assert report.total_points == 0
    assert report.winning_months == 0
    assert report.losing_months == 0
    assert report.win_rate == 0
    assert report.max_drawdown_points == 0
