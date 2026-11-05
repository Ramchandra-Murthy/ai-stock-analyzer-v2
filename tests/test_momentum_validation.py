"""Tests for research-only momentum score validation."""

import pytest

from ai_trading.momentum_validation import evaluate_momentum_scores


def test_report_summarizes_buckets_and_top_bottom_spread():
    rows = [
        {"momentum_score": 10, "forward_return_pct": -2.0},
        {"momentum_score": 35, "forward_return_pct": 1.0},
        {"momentum_score": 65, "forward_return_pct": 2.0},
        {"momentum_score": 85, "forward_return_pct": 4.0},
        {"momentum_score": 100, "forward_return_pct": 6.0},
    ]

    report = evaluate_momentum_scores(rows)

    assert report.observation_count == 5
    assert report.buckets[0].count == 1
    assert report.buckets[-1].count == 2
    assert report.top_bucket_mean_return_pct == pytest.approx(5.0)
    assert report.bottom_bucket_mean_return_pct == pytest.approx(-2.0)
    assert report.top_minus_bottom_return_pct == pytest.approx(7.0)
    assert report.score_return_correlation == pytest.approx(0.9807886628)


def test_empty_observations_return_none_metrics_and_zero_counts():
    report = evaluate_momentum_scores([])

    assert report.observation_count == 0
    assert report.mean_forward_return_pct is None
    assert report.win_rate_pct is None
    assert report.score_return_correlation is None
    assert all(bucket.count == 0 for bucket in report.buckets)


@pytest.mark.parametrize(
    "row",
    [
        {"momentum_score": -1, "forward_return_pct": 1},
        {"momentum_score": 101, "forward_return_pct": 1},
        {"momentum_score": 50, "forward_return_pct": float("nan")},
        {"momentum_score": float("inf"), "forward_return_pct": 1},
        {"momentum_score": 50},
    ],
)
def test_invalid_observations_are_rejected(row):
    with pytest.raises(ValueError):
        evaluate_momentum_scores([row])


def test_score_of_100_is_included_in_final_bucket():
    report = evaluate_momentum_scores([{"momentum_score": 100, "forward_return_pct": 3.5}])

    assert report.buckets[-1].count == 1
    assert report.buckets[-1].mean_forward_return_pct == pytest.approx(3.5)


def test_json_friendly_report_contains_bucket_summaries():
    report = evaluate_momentum_scores([{"momentum_score": 80, "forward_return_pct": 1.25}])

    payload = report.to_dict()
    assert payload["observation_count"] == 1
    assert payload["buckets"][-1]["count"] == 1
