"""Tests for the consolidated intraday quality dashboard."""

from services.intraday_quality_dashboard import dashboard_summary


def test_dashboard_summary_reports_session_counts():
    summary = dashboard_summary(
        {"RELIANCE": "TRIGGERED", "TCS": "WATCH"},
        {"RELIANCE": {"State": "TRIGGERED"}},
        {
            "RELIANCE": {"Price change %": 2.0},
            "TCS": {"Price change %": -1.0},
        },
        [{"Symbol": "RELIANCE"}],
        {
            "RELIANCE": {
                "5m change %": 1.0,
                "10m change %": None,
                "15m change %": None,
                "30m change %": None,
            }
        },
    )

    values = dict(zip(summary["Metric"], summary["Value"], strict=True))
    assert values["Active setup states"] == 2
    assert values["Persisting setups"] == 1
    assert values["Observed setup outcomes"] == 2
    assert values["State transitions"] == 1
    assert values["Positive observed outcomes"] == 1
    assert values["Negative observed outcomes"] == 1
    assert values["5m windows filled"] == 1
    assert values["10m windows filled"] == 0


def test_dashboard_summary_has_stable_empty_output():
    summary = dashboard_summary({}, {}, {}, [], {})

    assert list(summary.columns) == ["Metric", "Value"]
    assert len(summary) == 10
