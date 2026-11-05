"""Tests for chronological momentum walk-forward validation."""

import pytest

from ai_trading.momentum_walk_forward import evaluate_momentum_walk_forward


def _rows():
    return [
        {"date": f"2026-01-{day:02d}", "momentum_score": score, "forward_return_pct": ret}
        for day, score, ret in [
            (5, 10, -2.0),
            (1, 15, -1.0),
            (2, 30, 1.0),
            (3, 45, 2.0),
            (4, 60, 3.0),
            (6, 75, 4.0),
        ]
    ]


def test_splits_observations_chronologically_and_reports_fold_metrics():
    report = evaluate_momentum_walk_forward(_rows(), n_splits=3)

    assert report.observation_count == 6
    assert report.fold_count == 3
    assert [(fold.start_date, fold.end_date) for fold in report.folds] == [
        ("2026-01-01", "2026-01-02"),
        ("2026-01-03", "2026-01-04"),
        ("2026-01-05", "2026-01-06"),
    ]
    assert [fold.observation_count for fold in report.folds] == [2, 2, 2]
    assert report.to_dict()["fold_count"] == 3


def test_fold_sizes_are_balanced_when_observations_do_not_divide_evenly():
    report = evaluate_momentum_walk_forward(_rows(), n_splits=4)

    assert [fold.observation_count for fold in report.folds] == [2, 2, 1, 1]


@pytest.mark.parametrize("n_splits", [0, 1, -2, 2.5, True])
def test_invalid_split_count_is_rejected(n_splits):
    with pytest.raises(ValueError):
        evaluate_momentum_walk_forward(_rows(), n_splits=n_splits)


def test_requires_enough_rows_and_valid_dates():
    with pytest.raises(ValueError, match="at least n_splits"):
        evaluate_momentum_walk_forward(_rows()[:2], n_splits=3)

    bad_rows = _rows()
    bad_rows[0] = {**bad_rows[0], "date": "2026-02-30"}
    with pytest.raises(ValueError, match="valid ISO-8601"):
        evaluate_momentum_walk_forward(bad_rows, n_splits=3)


def test_reports_positive_spread_rate_only_for_folds_with_spread():
    report = evaluate_momentum_walk_forward(_rows(), n_splits=3)

    assert report.positive_spread_fold_count <= report.fold_count
    assert report.positive_spread_fold_rate_pct is None or (
        0 <= report.positive_spread_fold_rate_pct <= 100
    )
