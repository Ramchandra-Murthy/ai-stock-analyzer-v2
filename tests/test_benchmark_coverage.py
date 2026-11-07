"""Tests for historical benchmark coverage diagnostics."""

import pandas as pd
import pytest

from ai_trading.benchmark_coverage import summarize_benchmark_coverage


def test_coverage_uses_all_rows_for_nifty_and_only_mapped_rows_for_sector():
    history = pd.DataFrame(
        {
            "benchmark_status": [
                "matched_daily_close_proxy",
                "missing_outcome_benchmark_close",
                "benchmark_data_unavailable",
            ],
            "sector_benchmark_name": ["^CNXIT", pd.NA, "^NSEBANK"],
            "sector_benchmark_status": [
                "matched_daily_close_proxy",
                "sector_unmapped",
                "benchmark_data_unavailable",
            ],
        }
    )

    result = summarize_benchmark_coverage(history).set_index("benchmark")
    nifty = result.loc["NIFTY 50"]
    sector = result.loc["Mapped sector index"]

    assert nifty["eligible_observations"] == 3
    assert nifty["matched_observations"] == 1
    assert nifty["unmatched_observations"] == 2
    assert nifty["coverage_pct"] == pytest.approx(100 / 3)
    assert "missing_outcome_benchmark_close: 1" in nifty["status_breakdown"]

    assert sector["eligible_observations"] == 2
    assert sector["matched_observations"] == 1
    assert sector["unmatched_observations"] == 1
    assert sector["coverage_pct"] == pytest.approx(50.0)


def test_missing_status_is_counted_as_unknown_not_matched():
    history = pd.DataFrame(
        {
            "benchmark_status": [pd.NA],
            "sector_benchmark_name": ["^CNXIT"],
            "sector_benchmark_status": [pd.NA],
        }
    )

    result = summarize_benchmark_coverage(history)

    assert result.loc[0, "matched_observations"] == 0
    assert result.loc[0, "status_breakdown"] == "status_missing: 1"
    assert result.loc[1, "status_breakdown"] == "status_missing: 1"


def test_empty_history_returns_stable_schema():
    result = summarize_benchmark_coverage(pd.DataFrame())

    assert result.empty
    assert list(result.columns) == [
        "benchmark",
        "eligible_observations",
        "matched_observations",
        "unmatched_observations",
        "coverage_pct",
        "status_breakdown",
    ]


def test_missing_sector_mapping_excludes_all_rows_from_sector_denominator():
    history = pd.DataFrame(
        {
            "benchmark_status": ["matched_daily_close_proxy"],
            "sector_benchmark_status": ["sector_unmapped"],
        }
    )

    result = summarize_benchmark_coverage(history)

    assert result.loc[1, "eligible_observations"] == 0
    assert pd.isna(result.loc[1, "coverage_pct"])
