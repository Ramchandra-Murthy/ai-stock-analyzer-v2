from datetime import date

import pandas as pd

from services.data_quality import last_bar_date, split_stale


def _series(dates: list[str]) -> pd.Series:
    return pd.Series(range(len(dates)), index=pd.to_datetime(dates), dtype="float64")


def test_last_bar_date_reads_datetime_index() -> None:
    assert last_bar_date(_series(["2026-10-29", "2026-10-30"])) == date(2026, 10, 30)


def test_last_bar_date_handles_timezone_aware_index() -> None:
    series = _series(["2026-10-30"])
    series.index = series.index.tz_localize("Asia/Kolkata")
    assert last_bar_date(series) == date(2026, 10, 30)


def test_last_bar_date_is_none_for_empty_or_non_date_index() -> None:
    assert last_bar_date(None) is None
    assert last_bar_date(pd.Series(dtype="float64")) is None
    assert last_bar_date(pd.DataFrame({"Close": [1.0, 2.0]})) is None


def test_split_stale_flags_tickers_behind_the_latest_session() -> None:
    reference, stale = split_stale(
        {
            "FRESH.NS": date(2026, 10, 30),
            "ALSO_FRESH.NS": date(2026, 10, 30),
            "HALTED.NS": date(2026, 10, 27),
        }
    )
    assert reference == date(2026, 10, 30)
    assert stale == ["HALTED.NS"]


def test_split_stale_treats_unknown_date_as_stale() -> None:
    reference, stale = split_stale({"A.NS": date(2026, 10, 30), "B.NS": None})
    assert reference == date(2026, 10, 30)
    assert stale == ["B.NS"]


def test_split_stale_ignores_future_dated_bars_when_choosing_reference() -> None:
    reference, stale = split_stale(
        {"OK.NS": date(2026, 10, 30), "BOGUS.NS": date(2026, 12, 25)},
        today=date(2026, 10, 30),
    )
    assert reference == date(2026, 10, 30)
    assert stale == ["BOGUS.NS"]


def test_split_stale_with_no_usable_dates_returns_everything_stale() -> None:
    assert split_stale({}) == (None, [])
    assert split_stale({"A.NS": None}) == (None, ["A.NS"])



def test_filter_stale_frames_excludes_symbols_behind_batch_reference() -> None:
    from services.data_quality import filter_stale_frames

    frames = {
        "FRESH.NS": pd.DataFrame(
            {"Close": [100.0, 101.0]},
            index=pd.to_datetime(["2026-10-29", "2026-10-30"]),
        ),
        "HALTED.NS": pd.DataFrame(
            {"Close": [50.0, 51.0]},
            index=pd.to_datetime(["2026-10-27", "2026-10-28"]),
        ),
    }

    usable, status = filter_stale_frames(frames, today=date(2026, 10, 30))

    assert list(usable) == ["FRESH.NS"]
    assert status == {
        "reference_session": "2026-10-30",
        "stale_symbols": ["HALTED.NS"],
        "checked_symbols": 2,
        "usable_symbols": 1,
        "policy": "relative_latest_session",
    }


def test_filter_stale_frames_rejects_future_and_unknown_dates() -> None:
    from services.data_quality import filter_stale_frames

    frames = {
        "VALID.NS": pd.DataFrame(
            {"Close": [100.0]},
            index=pd.to_datetime(["2026-10-30"]),
        ),
        "FUTURE.NS": pd.DataFrame(
            {"Close": [100.0]},
            index=pd.to_datetime(["2026-12-25"]),
        ),
        "UNKNOWN.NS": pd.DataFrame({"Close": [100.0]}),
    }

    usable, status = filter_stale_frames(frames, today=date(2026, 10, 30))

    assert list(usable) == ["VALID.NS"]
    assert status["stale_symbols"] == ["FUTURE.NS", "UNKNOWN.NS"]
