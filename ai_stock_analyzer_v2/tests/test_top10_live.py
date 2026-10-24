from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import components.top10_live as top10_live
from components.top10_live import (
    TOP10_CACHE_SECONDS,
    TOP10_CHUNK_SIZE,
    TOP10_COVERAGE_KEY,
    TOP10_EXPECTED_QUOTES,
    TOP10_GOOD_COVERAGE_QUOTES,
    TOP10_MARKET_CLOSE_HOUR,
    TOP10_MARKET_CLOSE_MINUTE,
    TOP10_MARKET_OPEN_HOUR,
    TOP10_MARKET_OPEN_MINUTE,
    TOP10_MAX_BSE_CANDIDATES,
    TOP10_MAX_CONSECUTIVE_FAILURES,
    TOP10_MAX_NSE_CANDIDATES,
    TOP10_MIN_TRUSTED_COVERAGE_QUOTES,
    TOP10_PARTIAL_FAILURES_KEY,
    TOP10_PERSISTENCE_ALERT_MIN_SCANS,
    TOP10_PERSISTENCE_MIN_SCANS,
    TOP10_PROVIDER_RETRIES,
    TOP10_PROVIDER_TIMEOUT,
    TOP10_REDUCED_COVERAGE_QUOTES,
    TOP10_REFRESH_SECONDS,
    TOP10_SCAN_WARNING_SECONDS,
    TOP10_SESSION_STATUS_KEY,
    TOP10_SIGNAL_HISTORY_KEY,
    TOP10_SIGNAL_HISTORY_LIMIT,
    TOP10_STALE_DATA_SECONDS,
    TOP10_TIMEZONE,
    _add_signal_history,
    _add_signal_persistence,
    _add_signal_strength,
    _annotate_watchlist_changes,
    _calculate_signal_strength,
    _coverage_status,
    _format_candle_time,
    _is_fresh_provider_timestamp,
    _persistence_alerts,
    _provider_age_seconds,
    _scan_live_top10,
    _should_record_signal_history,
    _signal_confirmation,
    _signal_history_table,
    _signal_history_trend,
    _signal_persistence,
    _signal_quality_metrics,
    _start_background_scan,
    _update_signal_history,
    _watchlist_change_alerts,
    show_live_top10_scanner,
)
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES


def test_top10_live_scanner_refreshes_every_minute() -> None:
    assert TOP10_REFRESH_SECONDS == 60
    assert TOP10_CACHE_SECONDS < TOP10_REFRESH_SECONDS
    assert TOP10_CHUNK_SIZE == 20
    assert TOP10_MAX_NSE_CANDIDATES == 10
    assert TOP10_MAX_BSE_CANDIDATES == 10
    assert TOP10_PROVIDER_RETRIES == 0
    assert TOP10_PROVIDER_TIMEOUT == 5
    assert TOP10_MAX_CONSECUTIVE_FAILURES == 2
    assert 0 < TOP10_SCAN_WARNING_SECONDS < TOP10_STALE_DATA_SECONDS
    assert TOP10_STALE_DATA_SECONDS >= 3 * TOP10_REFRESH_SECONDS
    assert callable(show_live_top10_scanner)
    assert callable(_scan_live_top10)
    assert callable(_start_background_scan)
    assert "REFRESHING" in open("components/top10_live.py", encoding="utf-8").read()
    assert "FRESH" in open("components/top10_live.py", encoding="utf-8").read()


def test_top10_live_uses_a_bounded_nse_pool_for_faster_quote_refresh() -> None:
    assert TOP10_MAX_NSE_CANDIDATES == 10
    assert TOP10_MAX_BSE_CANDIDATES == 10
    assert TOP10_EXPECTED_QUOTES == 20


def test_top10_live_uses_india_timezone() -> None:
    assert TOP10_TIMEZONE == "Asia/Kolkata"
    assert ZoneInfo(TOP10_TIMEZONE).key == "Asia/Kolkata"


def test_top10_live_refresh_starts_when_interval_is_due() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "refresh_due" in source
    assert "now >= completed_at + timedelta" in source
    assert "seconds=TOP10_REFRESH_SECONDS" in source


def test_top10_market_session_hours() -> None:
    assert (TOP10_MARKET_OPEN_HOUR, TOP10_MARKET_OPEN_MINUTE) == (9, 15)
    assert (TOP10_MARKET_CLOSE_HOUR, TOP10_MARKET_CLOSE_MINUTE) == (15, 30)


def test_top10_live_session_status_key() -> None:
    assert TOP10_SESSION_STATUS_KEY == "top10_market_status"


def test_top10_live_tracks_data_freshness() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "data_age_seconds" in source
    assert "STALE DATA" in source
    assert "st.session_state[TOP10_SESSION_STATUS_KEY]" in source


def test_top10_live_rejects_stale_and_unknown_candle_timestamps() -> None:
    now = datetime(2026, 10, 5, 10, 0, tzinfo=ZoneInfo(TOP10_TIMEZONE))

    assert _is_fresh_provider_timestamp("2026-10-05T09:59:00+05:30", now)
    assert not _is_fresh_provider_timestamp("2026-10-05T09:55:00+05:30", now)
    assert not _is_fresh_provider_timestamp("not-a-timestamp", now)


def test_top10_live_formats_candle_times_in_ist() -> None:
    assert _format_candle_time("2026-10-05 09:59:00") == "2026-10-05 09:59:00 IST"
    assert _format_candle_time("2026-10-05T09:59:00+00:00") == "2026-10-05 15:29:00 IST"
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "tz_convert(_IST)" in source
    assert "Last candle" in source


def test_top10_live_exposes_partial_provider_failures() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert TOP10_PARTIAL_FAILURES_KEY == "top10_partial_failures"
    assert "partial_failures" in source
    assert "PARTIAL PROVIDER ISSUE" in source
    assert "Provider failures" in source


def test_top10_live_exposes_quote_coverage() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert TOP10_COVERAGE_KEY == "top10_quote_coverage"
    assert "valid_quotes" in source
    assert "Quotes {valid_quotes}/" in source


def test_top10_live_classifies_quote_coverage_quality() -> None:
    assert TOP10_COVERAGE_KEY == "top10_quote_coverage"
    assert TOP10_EXPECTED_QUOTES == 20
    assert TOP10_GOOD_COVERAGE_QUOTES == 18
    assert TOP10_REDUCED_COVERAGE_QUOTES == 10
    assert _coverage_status(20) == "GOOD"
    assert _coverage_status(18) == "GOOD"
    assert _coverage_status(17) == "REDUCED"
    assert _coverage_status(10) == "REDUCED"
    assert _coverage_status(9) == "CRITICAL"
    assert _coverage_status(0) == "CRITICAL"


def test_top10_live_displays_coverage_quality() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "Coverage {coverage_status}" in source
    assert "CRITICAL QUOTE COVERAGE" in source
    assert "REDUCED QUOTE COVERAGE" in source


def test_top10_live_tracks_membership_and_rank_changes() -> None:
    previous = pd.DataFrame(
        [
            {"Rank": 1, "Symbol": "AAA", "Exchange": "NSE"},
            {"Rank": 2, "Symbol": "BBB", "Exchange": "NSE"},
        ]
    )
    current = pd.DataFrame(
        [
            {"Rank": 1, "Symbol": "BBB", "Exchange": "NSE"},
            {"Rank": 2, "Symbol": "CCC", "Exchange": "NSE"},
        ]
    )

    annotated, dropped = _annotate_watchlist_changes(current, previous)

    assert annotated[["Symbol", "Status", "Rank change"]].to_dict("records") == [
        {"Symbol": "BBB", "Status": "UP", "Rank change": 1},
        {"Symbol": "CCC", "Status": "NEW", "Rank change": None},
    ]
    assert dropped == ["NSE:AAA"]


def test_top10_live_first_scan_marks_all_symbols_new() -> None:
    current = pd.DataFrame(
        [
            {"Rank": 1, "Symbol": "AAA", "Exchange": "NSE"},
            {"Rank": 2, "Symbol": "BBB", "Exchange": "BSE"},
        ]
    )

    annotated, dropped = _annotate_watchlist_changes(current, None)

    assert annotated["Status"].tolist() == ["NEW", "NEW"]
    assert annotated["Rank change"].tolist() == [None, None]
    assert dropped == []


def test_top10_live_alerts_material_watchlist_changes() -> None:
    annotated = pd.DataFrame(
        [
            {
                "Rank": 1,
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Status": "NEW",
                "Rank change": None,
                "1-min %": 1.25,
            },
            {
                "Rank": 2,
                "Symbol": "BBB",
                "Exchange": "NSE",
                "Status": "UP",
                "Rank change": 2,
                "1-min %": 0.2,
            },
            {
                "Rank": 3,
                "Symbol": "CCC",
                "Exchange": "BSE",
                "Status": "UNCHANGED",
                "Rank change": 0,
                "1-min %": 1.5,
            },
        ]
    )

    alerts = _watchlist_change_alerts(annotated)

    assert len(alerts) == 3
    assert "NEW · NSE:AAA" in alerts[0]
    assert "RANK UP · NSE:BBB · 2 places" in alerts[1]
    assert "MOVE · BSE:CCC · 1-min +1.50%" in alerts[2]


def test_top10_live_alerts_ignore_small_changes() -> None:
    annotated = pd.DataFrame(
        [
            {
                "Rank": 5,
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Status": "UNCHANGED",
                "Rank change": 1,
                "1-min %": 0.4,
            }
        ]
    )

    assert _watchlist_change_alerts(annotated) == []


def test_top10_live_calculates_signal_strength() -> None:
    score, direction = _calculate_signal_strength(
        {
            "Status": "NEW",
            "Rank change": 2,
            "1-min %": 1.5,
            "5-min %": 3.0,
        }
    )

    assert score == 56
    assert direction == "UP"


def test_top10_live_signal_direction_handles_mixed_moves() -> None:
    score, direction = _calculate_signal_strength(
        {
            "Status": "UNCHANGED",
            "Rank change": 0,
            "1-min %": 1.0,
            "5-min %": -1.0,
        }
    )

    assert score == 19
    assert direction == "MIXED"


def test_top10_live_signal_history_tracks_score_and_direction_changes() -> None:
    previous = pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Momentum score": 40,
                "Direction": "UP",
            },
            {
                "Symbol": "BBB",
                "Exchange": "BSE",
                "Momentum score": 70,
                "Direction": "DOWN",
            },
        ]
    )
    current = pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Momentum score": 55,
                "Direction": "UP",
            },
            {
                "Symbol": "BBB",
                "Exchange": "BSE",
                "Momentum score": 60,
                "Direction": "UP",
            },
            {
                "Symbol": "CCC",
                "Exchange": "NSE",
                "Momentum score": 30,
                "Direction": "MIXED",
            },
        ]
    )

    enriched = _add_signal_history(current, [previous])

    assert enriched[
        ["Symbol", "Previous score", "Score change", "Signal trend", "Direction change"]
    ].to_dict("records") == [
        {
            "Symbol": "AAA",
            "Previous score": 40,
            "Score change": 15,
            "Signal trend": "STRENGTHENING",
            "Direction change": "UNCHANGED",
        },
        {
            "Symbol": "BBB",
            "Previous score": 70,
            "Score change": -10,
            "Signal trend": "WEAKENING",
            "Direction change": "DOWN→UP",
        },
        {
            "Symbol": "CCC",
            "Previous score": None,
            "Score change": None,
            "Signal trend": "NEW",
            "Direction change": "NEW",
        },
    ]


def test_top10_live_signal_history_is_limited_to_ten_scans() -> None:
    assert TOP10_SIGNAL_HISTORY_LIMIT == 10
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert TOP10_SIGNAL_HISTORY_KEY == "top10_signal_history"
    assert "[-TOP10_SIGNAL_HISTORY_LIMIT:]" in source


def test_top10_live_adds_signal_columns() -> None:
    annotated = pd.DataFrame(
        [
            {
                "Rank": 1,
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Status": "NEW",
                "Rank change": None,
                "1-min %": 1.0,
                "5-min %": 2.0,
            }
        ]
    )

    enriched = _add_signal_strength(annotated)

    assert enriched[["Momentum score", "Direction"]].to_dict("records") == [
        {"Momentum score": 35, "Direction": "UP"}
    ]


def test_top10_live_signal_history_records_scan_time() -> None:
    annotated = pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Momentum score": 55,
                "Direction": "UP",
            }
        ]
    )
    completed_at = datetime(2026, 10, 3, 10, 30, tzinfo=ZoneInfo(TOP10_TIMEZONE))

    history = _update_signal_history([], annotated, completed_at)

    assert history[0]["Scan time"].iloc[0] == completed_at
    assert history[0]["Symbol"].tolist() == ["AAA"]


def test_top10_live_signal_history_table_and_trend() -> None:
    first_time = datetime(2026, 10, 3, 10, 30, tzinfo=ZoneInfo(TOP10_TIMEZONE))
    second_time = datetime(2026, 10, 3, 10, 31, tzinfo=ZoneInfo(TOP10_TIMEZONE))
    history = [
        pd.DataFrame(
            [
                {
                    "Scan time": first_time,
                    "Symbol": "AAA",
                    "Exchange": "NSE",
                    "Momentum score": 40,
                    "Direction": "UP",
                }
            ]
        ),
        pd.DataFrame(
            [
                {
                    "Scan time": second_time,
                    "Symbol": "AAA",
                    "Exchange": "NSE",
                    "Momentum score": 65,
                    "Direction": "UP",
                }
            ]
        ),
    ]

    table = _signal_history_table(history)
    trend = _signal_history_trend(history)

    assert table.shape[0] == 2
    assert table["Momentum score"].tolist() == [40, 65]
    assert list(trend.columns) == ["NSE:AAA"]
    assert trend["NSE:AAA"].tolist() == [40, 65]
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "st.line_chart(history_trend)" in source
    assert "st.line_chart(history_trend, y_min=0, y_max=100)" not in source


def test_top10_live_history_chart_uses_supported_streamlit_api() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "st.line_chart(history_trend)" in source
    assert "st.line_chart(history_trend, y_min=" not in source


def test_top10_live_signal_persistence_counts_consecutive_presence_and_direction() -> None:
    history = [
        pd.DataFrame(
            [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 30, "Direction": "UP"}]
        ),
        pd.DataFrame(
            [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 45, "Direction": "UP"}]
        ),
        pd.DataFrame(
            [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 55, "Direction": "UP"}]
        ),
    ]

    assert _signal_persistence(history)[("NSE", "AAA")] == (3, "UP")


def test_top10_live_signal_persistence_breaks_after_missing_scan() -> None:
    history = [
        pd.DataFrame(
            [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 30, "Direction": "UP"}]
        ),
        pd.DataFrame(
            [{"Symbol": "BBB", "Exchange": "NSE", "Momentum score": 45, "Direction": "UP"}]
        ),
        pd.DataFrame(
            [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 55, "Direction": "UP"}]
        ),
    ]

    assert _signal_persistence(history)[("NSE", "AAA")] == (1, "UP")


def test_top10_live_adds_signal_persistence_columns() -> None:
    annotated = pd.DataFrame(
        [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 60, "Direction": "UP"}]
    )
    history = [
        pd.DataFrame(
            [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 45, "Direction": "UP"}]
        ),
        pd.DataFrame(
            [{"Symbol": "AAA", "Exchange": "NSE", "Momentum score": 60, "Direction": "UP"}]
        ),
    ]

    enriched = _add_signal_persistence(annotated, history)

    assert TOP10_PERSISTENCE_MIN_SCANS == 2
    assert enriched[["Persistence", "Persistent direction"]].to_dict("records") == [
        {"Persistence": 2, "Persistent direction": "UP"}
    ]


def test_top10_live_persistence_alerts_surface_consecutive_scans() -> None:
    annotated = pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Momentum score": 72,
                "Persistence": 3,
                "Persistent direction": "UP",
            },
            {
                "Symbol": "BBB",
                "Exchange": "BSE",
                "Momentum score": 61,
                "Persistence": 2,
                "Persistent direction": "DOWN",
            },
        ]
    )

    alerts = _persistence_alerts(annotated)

    assert TOP10_PERSISTENCE_ALERT_MIN_SCANS == 3
    assert alerts == ["🔁 PERSISTENT UP · NSE:AAA · 3 scans · score 72"]


def test_top10_live_persistence_alerts_ignore_short_or_mixed_persistence() -> None:
    annotated = pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Momentum score": 50,
                "Persistence": 2,
                "Persistent direction": "UP",
            },
            {
                "Symbol": "BBB",
                "Exchange": "BSE",
                "Momentum score": 55,
                "Persistence": 4,
                "Persistent direction": "MIXED",
            },
        ]
    )

    assert _persistence_alerts(annotated) == ["🔁 PERSISTENT · BSE:BBB · 4 scans · score 55"]


def test_top10_live_signal_confirmation_uses_score_persistence_and_trend() -> None:
    confirmed = {
        "Momentum score": 65,
        "Persistence": 3,
        "Persistent direction": "UP",
        "Signal trend": "STRENGTHENING",
    }
    developing = {
        "Momentum score": 45,
        "Persistence": 2,
        "Persistent direction": "DOWN",
        "Signal trend": "STABLE",
    }
    weak = {
        "Momentum score": 35,
        "Persistence": 1,
        "Persistent direction": "MIXED",
        "Signal trend": "NEW",
    }

    assert _signal_confirmation(confirmed) == "CONFIRMED"
    assert _signal_confirmation(developing) == "DEVELOPING"
    assert _signal_confirmation(weak) == "WEAK"


def test_top10_live_adds_signal_confirmation_column() -> None:
    annotated = pd.DataFrame(
        [
            {
                "Symbol": "AAA",
                "Exchange": "NSE",
                "Momentum score": 65,
                "Persistence": 3,
                "Persistent direction": "UP",
                "Signal trend": "STRENGTHENING",
            }
        ]
    )

    from components.top10_live import _add_signal_confirmation

    enriched = _add_signal_confirmation(annotated)

    assert enriched["Signal confirmation"].tolist() == ["CONFIRMED"]


def test_top10_live_signal_quality_metrics_summarize_scan_history() -> None:
    history = [
        pd.DataFrame(
            [
                {
                    "Signal confirmation": "CONFIRMED",
                    "Persistence": 3,
                    "Persistent direction": "UP",
                    "Signal trend": "STRENGTHENING",
                },
                {
                    "Signal confirmation": "DEVELOPING",
                    "Persistence": 2,
                    "Persistent direction": "DOWN",
                    "Signal trend": "STABLE",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    "Signal confirmation": "WEAK",
                    "Persistence": 1,
                    "Persistent direction": "MIXED",
                    "Signal trend": "NEW",
                },
                {
                    "Signal confirmation": "CONFIRMED",
                    "Persistence": 4,
                    "Persistent direction": "UP",
                    "Signal trend": "WEAKENING",
                },
            ]
        ),
    ]

    assert _signal_quality_metrics(history) == {
        "Confirmation rate": 50.0,
        "Persistence rate": 75.0,
        "Direction consistency": 75.0,
        "Momentum consistency": 50.0,
    }


def test_top10_live_signal_quality_metrics_handle_empty_history() -> None:
    assert _signal_quality_metrics([]) == {
        "Confirmation rate": 0.0,
        "Persistence rate": 0.0,
        "Direction consistency": 0.0,
        "Momentum consistency": 0.0,
    }


def test_top10_live_only_records_history_from_trusted_complete_fresh_scans() -> None:
    assert TOP10_MIN_TRUSTED_COVERAGE_QUOTES == TOP10_GOOD_COVERAGE_QUOTES
    assert _should_record_signal_history(20, 0, 60.0) is True
    assert _should_record_signal_history(18, 0, 60.0) is True
    assert _should_record_signal_history(17, 0, 60.0) is False
    assert _should_record_signal_history(20, 1, 60.0) is False
    assert _should_record_signal_history(20, 0, TOP10_STALE_DATA_SECONDS) is False
    assert _should_record_signal_history(20, 0, None) is False
    assert _should_record_signal_history(20, 0, -1.0) is False


def test_top10_live_uses_provider_candle_age() -> None:
    now = datetime(2026, 10, 5, 10, 0, tzinfo=ZoneInfo(TOP10_TIMEZONE))
    assert _provider_age_seconds("2026-10-05T09:59:00+05:30", now) == 60.0
    assert _provider_age_seconds("not-a-timestamp", now) is None
    assert _provider_age_seconds("2026-10-05T10:01:01+05:30", now) is None


def test_top10_live_avoids_missing_ticker_recovery_storm() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "retries=TOP10_PROVIDER_RETRIES" in source
    assert "recover_missing=False" in source


def test_top10_scan_excludes_symbols_with_stale_latest_candles(monkeypatch) -> None:
    now = pd.Timestamp.now(tz=TOP10_TIMEZONE)
    fresh_timestamp = now - pd.Timedelta(seconds=30)
    stale_timestamp = now - pd.Timedelta(minutes=10)
    tickers = [
        *(
            top10_live._ticker(symbol, "NSE")
            for symbol in NSE_CANDIDATES[:TOP10_MAX_NSE_CANDIDATES]
        ),
        *(
            top10_live._ticker(symbol, "BSE")
            for symbol in BSE_CANDIDATES[:TOP10_MAX_BSE_CANDIDATES]
        ),
    ]
    frames = {}
    for ticker in tickers:
        timestamp = fresh_timestamp if ticker == tickers[0] else stale_timestamp
        frames[ticker] = pd.DataFrame(
            {"Close": [100.0, 101.0]},
            index=[timestamp - pd.Timedelta(minutes=1), timestamp],
        )

    monkeypatch.setattr(
        top10_live,
        "_download_top10_frames",
        lambda requested_tickers: (frames, [], "Test provider"),
    )

    result, _elapsed, failures, valid_quotes = _scan_live_top10()

    assert failures == 0
    assert valid_quotes == 1
    assert result["Symbol"].tolist() == [tickers[0].rsplit(".", 1)[0]]
    assert result["Last candle"].tolist() == [top10_live._format_candle_time(fresh_timestamp)]


def test_top10_background_refresh_is_polled_faster_than_scan_interval() -> None:
    assert top10_live.TOP10_UI_POLL_SECONDS < top10_live.TOP10_REFRESH_SECONDS
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert '@st.fragment(run_every=f"{TOP10_UI_POLL_SECONDS}s")' in source


def test_top10_scanner_displays_safe_provider_diagnostics() -> None:
    source = open("components/top10_live.py", encoding="utf-8").read()
    assert "Provider diagnostics (safe summary)" in source
    assert "Quote provider:" in source
    assert "diagnostics=_PROVIDER_DIAGNOSTICS" in source
