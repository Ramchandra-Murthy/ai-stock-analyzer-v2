import pandas as pd
import pytest

from ai_trading.benchmark_capture import benchmark_capture


def test_benchmark_capture_reports_upside_and_downside_participation() -> None:
    benchmark = pd.Series([0.10, -0.10, 0.05, -0.05])
    strategy = benchmark * 0.5

    report = benchmark_capture(strategy, benchmark)

    assert report["observations"] == 4
    assert report["upside_capture"] == pytest.approx(((1.05 * 1.025) - 1.0) / ((1.10 * 1.05) - 1.0))
    assert report["downside_capture"] == pytest.approx(
        ((0.95 * 0.975) - 1.0) / ((0.90 * 0.95) - 1.0)
    )


def test_benchmark_capture_handles_empty_aligned_returns() -> None:
    report = benchmark_capture(
        pd.Series([0.01], index=[0]),
        pd.Series([0.02], index=[1]),
    )

    assert report == {
        "observations": 0,
        "upside_capture": None,
        "downside_capture": None,
    }
