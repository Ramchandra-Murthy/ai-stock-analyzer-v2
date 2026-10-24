import pandas as pd
import pytest

from ai_trading.lookahead import (
    assert_no_future_observations,
    assert_no_label_lookahead,
    assert_no_timestamp_lookahead,
)


def test_future_observations_are_rejected():
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01 09:15",
                "2026-01-01 09:20",
                "2026-01-01 09:25",
            ]
        }
    )

    with pytest.raises(ValueError, match="lookahead detected"):
        assert_no_future_observations(
            frame,
            timestamp_column="timestamp",
            as_of="2026-01-01 09:20",
        )


def test_observations_at_decision_time_are_allowed():
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01 09:15",
                "2026-01-01 09:20",
            ]
        }
    )

    assert_no_future_observations(
        frame,
        timestamp_column="timestamp",
        as_of="2026-01-01 09:20",
    )


def test_feature_timestamps_after_decision_are_rejected():
    source = pd.Series(pd.to_datetime(["2026-01-01 09:20", "2026-01-01 09:30"]))
    decisions = pd.Series(pd.to_datetime(["2026-01-01 09:20", "2026-01-01 09:25"]))

    with pytest.raises(ValueError, match="lookahead detected"):
        assert_no_timestamp_lookahead(source, decisions, source_name="feature timestamps")


def test_label_end_at_decision_time_is_allowed():
    label_end = pd.Series(pd.to_datetime(["2026-01-01 09:20", "2026-01-01 09:25"]))
    decisions = pd.Series(pd.to_datetime(["2026-01-01 09:20", "2026-01-01 09:25"]))

    assert_no_label_lookahead(label_end, decisions)


def test_label_end_after_decision_is_rejected():
    label_end = pd.Series(pd.to_datetime(["2026-01-01 09:20", "2026-01-01 09:30"]))
    decisions = pd.Series(pd.to_datetime(["2026-01-01 09:20", "2026-01-01 09:25"]))

    with pytest.raises(ValueError, match="lookahead detected"):
        assert_no_label_lookahead(label_end, decisions)


def test_timestamp_validation_rejects_invalid_values():
    source = pd.Series(["2026-01-01", "not-a-date"])
    decisions = pd.Series(["2026-01-01", "2026-01-02"])

    with pytest.raises(ValueError, match="invalid or missing"):
        assert_no_timestamp_lookahead(source, decisions)


def test_timestamp_validation_requires_matching_lengths():
    source = pd.Series(pd.to_datetime(["2026-01-01"]))
    decisions = pd.Series(pd.to_datetime(["2026-01-01", "2026-01-02"]))

    with pytest.raises(ValueError, match="same length"):
        assert_no_timestamp_lookahead(source, decisions)
