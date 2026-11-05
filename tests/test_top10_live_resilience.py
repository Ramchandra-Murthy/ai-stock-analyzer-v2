"""Behavioural tests for the live Top-10 scanner's failure handling.

They drive the real scan, recovery and refresh code with mocked provider responses
and a recording stand-in for Streamlit, so they exercise behaviour rather than
grepping source text.
"""

from __future__ import annotations

import ast
import itertools
from concurrent.futures import Future
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

import components.top10_live as top10_live
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES

IST = ZoneInfo(top10_live.TOP10_TIMEZONE)
# A Thursday inside the regular 09:15-15:30 IST session.
MARKET_OPEN = datetime(2026, 11, 5, 11, 0, tzinfo=IST)
MARKET_CLOSED = datetime(2026, 11, 5, 18, 0, tzinfo=IST)

NSE_TICKERS = [top10_live._ticker(s, "NSE") for s in NSE_CANDIDATES[:10]]
BSE_TICKERS = [top10_live._ticker(s, "BSE") for s in BSE_CANDIDATES[:10]]
ALL_TICKERS = [*NSE_TICKERS, *BSE_TICKERS]


# --------------------------------------------------------------------------- helpers


class _ManualExecutor:
    """Executor stand-in whose queued scans finish only when the test says so."""

    def __init__(self) -> None:
        self.pending: list[tuple[Future, object, tuple]] = []
        self.shutdown_calls = 0

    def submit(self, fn, *args):
        future: Future = Future()
        self.pending.append((future, fn, args))
        return future

    def run_pending(self) -> None:
        pending, self.pending = self.pending, []
        for future, fn, args in pending:
            try:
                future.set_result(fn(*args))
            except Exception as exc:
                future.set_exception(exc)

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        self.shutdown_calls += 1


class _Clock:
    """Controllable replacement for ``datetime.now`` inside the scanner module."""

    def __init__(self, start: datetime) -> None:
        self.current = start

    def advance(self, **kwargs: float) -> datetime:
        self.current += timedelta(**kwargs)
        return self.current

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clock = self

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.current.astimezone(tz) if tz else clock.current

        monkeypatch.setattr(top10_live, "datetime", _FrozenDatetime)


class _Slot:
    def __enter__(self) -> _Slot:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def container(self) -> _Slot:
        return _Slot()

    def __getattr__(self, _name: str):
        return lambda *_args, **_kwargs: None


class _Recorder:
    def __getattr__(self, _name: str):
        return lambda *_args, **_kwargs: None


class _FakeStreamlit:
    """Records the elements a render emits so tests can count and read them."""

    WIDGETS = ("button", "selectbox", "number_input", "text_input", "checkbox", "radio")

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.session_state: dict[str, object] = {}
        self.column_config = _Recorder()
        self.button_pressed = False

    def _log(self, kind: str, text: object = "") -> None:
        self.calls.append((kind, str(text)))

    def subheader(self, text: object = "", *_a: object, **_k: object) -> None:
        self._log("subheader", text)

    def caption(self, text: object = "", *_a: object, **_k: object) -> None:
        self._log("caption", text)

    def info(self, text: object = "", *_a: object, **_k: object) -> None:
        self._log("info", text)

    def warning(self, text: object = "", *_a: object, **_k: object) -> None:
        self._log("warning", text)

    def error(self, text: object = "", *_a: object, **_k: object) -> None:
        self._log("error", text)

    def dataframe(self, data: object = None, *_a: object, **_k: object) -> None:
        self._log("dataframe", ",".join(str(column) for column in getattr(data, "columns", [])))

    def line_chart(self, *_a: object, **_k: object) -> None:
        self._log("line_chart")

    def button(self, label: object = "", *_a: object, **_k: object) -> bool:
        self._log("button", label)
        return self.button_pressed

    def selectbox(self, *_a: object, **_k: object) -> None:
        self._log("selectbox")

    def number_input(self, *_a: object, **_k: object) -> float:
        self._log("number_input")
        return 0.0

    def expander(self, *_a: object, **_k: object) -> _Slot:
        return _Slot()

    def empty(self) -> _Slot:
        return _Slot()

    def columns(self, spec: object, *_a: object, **_k: object) -> list[_Slot]:
        count = spec if isinstance(spec, int) else len(spec)  # type: ignore[arg-type]
        return [_Slot() for _ in range(count)]

    def __getattr__(self, name: str):
        return lambda *_args, **_kwargs: self._log(name)

    def kinds(self, kind: str) -> list[str]:
        return [text for call_kind, text in self.calls if call_kind == kind]

    def widget_count(self) -> int:
        return sum(1 for kind, _ in self.calls if kind in self.WIDGETS)

    def top10_tables(self) -> int:
        """Main Top-10 tables rendered; the signal-history table has no Rank column."""
        return sum(1 for text in self.kinds("dataframe") if "Rank" in text.split(","))


class _Cache:
    cleared = 0

    @classmethod
    def clear(cls) -> None:
        cls.cleared += 1


def _fresh_frame(now: pd.Timestamp, *, age_seconds: float, closes=(100.0, 101.0)) -> pd.DataFrame:
    latest = now - pd.Timedelta(seconds=age_seconds)
    index = [latest - pd.Timedelta(minutes=len(closes) - 1 - i) for i in range(len(closes))]
    return pd.DataFrame({"Close": list(closes)}, index=index)


def _sample_result(
    now: datetime,
    *,
    symbols: tuple[str, ...] = ("AAA", "BBB"),
    provider_failures: int = 0,
    quotes: int = 20,
) -> tuple[pd.DataFrame, float, int, int]:
    stamp = pd.Timestamp(now) - pd.Timedelta(seconds=30)
    frame = pd.DataFrame(
        {
            "Rank": list(range(1, len(symbols) + 1)),
            "Symbol": list(symbols),
            "Exchange": ["NSE"] * len(symbols),
            "Price": [100.0 + i for i in range(len(symbols))],
            "1-min %": [1.5 - i for i in range(len(symbols))],
            "5-min %": [2.0] * len(symbols),
            "Last candle": [top10_live._format_candle_time(stamp)] * len(symbols),
        }
    )
    frame.attrs["provider"] = "Test provider"
    frame.attrs["latest_candle_at"] = stamp
    return frame, 3.2, provider_failures, quotes


@pytest.fixture
def executor(monkeypatch: pytest.MonkeyPatch) -> _ManualExecutor:
    manual = _ManualExecutor()
    top10_live._reset_scan_state()
    monkeypatch.setattr(top10_live, "_SCAN_EXECUTOR", manual)
    yield manual
    top10_live._reset_scan_state()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake_clock = _Clock(MARKET_OPEN)
    fake_clock.install(monkeypatch)
    return fake_clock


@pytest.fixture
def fake_st(monkeypatch: pytest.MonkeyPatch) -> _FakeStreamlit:
    fake = _FakeStreamlit()
    monkeypatch.setattr(top10_live, "st", fake)
    monkeypatch.setattr(top10_live, "_load_live_top10", _Cache)
    return fake


def _scripted_scans(monkeypatch: pytest.MonkeyPatch, outcomes: list[object]) -> list[int]:
    """Make ``_scan_live_top10`` return/raise the scripted outcomes in order."""
    calls: list[int] = []
    queue = iter(outcomes)

    def fake_scan():
        calls.append(1)
        outcome = next(queue)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(top10_live, "_scan_live_top10", fake_scan)
    return calls


# ----------------------------------------------- scan: partial / zero / fabricated data


def test_scan_shows_valid_quotes_when_some_symbols_are_missing(monkeypatch) -> None:
    """Regression: one unresolved ticker used to crash the whole scan."""
    now = pd.Timestamp.now(tz=top10_live.TOP10_TIMEZONE)
    frames = {ticker: _fresh_frame(now, age_seconds=20) for ticker in NSE_TICKERS}
    monkeypatch.setattr(
        top10_live,
        "_download_top10_frames",
        lambda _tickers: (frames, BSE_TICKERS, "Test provider"),
    )

    result, _elapsed, failures, valid_quotes = top10_live._scan_live_top10()

    assert failures == len(BSE_TICKERS)
    assert valid_quotes == len(NSE_TICKERS)
    assert set(result["Exchange"]) == {"NSE"}
    assert len(result) == len(NSE_TICKERS)


def test_scan_rows_come_only_from_provider_candles(monkeypatch) -> None:
    now = pd.Timestamp.now(tz=top10_live.TOP10_TIMEZONE)
    frames = {
        NSE_TICKERS[0]: _fresh_frame(now, age_seconds=10, closes=(200.0, 210.0)),
        NSE_TICKERS[1]: _fresh_frame(now, age_seconds=10, closes=(50.0, 49.0)),
    }
    monkeypatch.setattr(
        top10_live,
        "_download_top10_frames",
        lambda _tickers: (frames, [t for t in ALL_TICKERS if t not in frames], "Test provider"),
    )

    result, _elapsed, _failures, valid_quotes = top10_live._scan_live_top10()

    assert valid_quotes == 2
    by_symbol = result.set_index("Symbol")
    first = NSE_TICKERS[0].rsplit(".", 1)[0]
    second = NSE_TICKERS[1].rsplit(".", 1)[0]
    assert by_symbol.loc[first, "Price"] == 210.0
    assert by_symbol.loc[first, "1-min %"] == 5.0
    assert by_symbol.loc[second, "Price"] == 49.0
    assert by_symbol.loc[second, "1-min %"] == -2.0
    assert set(result["Symbol"]) == {first, second}


def test_scan_with_no_provider_data_raises_a_clear_error(monkeypatch) -> None:
    monkeypatch.setattr(
        top10_live,
        "_download_top10_frames",
        lambda _tickers: ({}, list(ALL_TICKERS), "Test provider"),
    )

    with pytest.raises(top10_live.Top10ScanError) as excinfo:
        top10_live._scan_live_top10()

    message = str(excinfo.value)
    assert "No usable live quotes" in message
    assert f"0 of {len(ALL_TICKERS)}" in message
    assert f"{len(ALL_TICKERS)} missing from the provider" in message


def test_scan_with_only_stale_candles_reports_staleness(monkeypatch) -> None:
    now = pd.Timestamp.now(tz=top10_live.TOP10_TIMEZONE)
    frames = {ticker: _fresh_frame(now, age_seconds=15 * 60) for ticker in ALL_TICKERS}
    monkeypatch.setattr(
        top10_live,
        "_download_top10_frames",
        lambda _tickers: (frames, [], "Test provider"),
    )

    with pytest.raises(top10_live.Top10ScanError) as excinfo:
        top10_live._scan_live_top10()

    assert f"{len(ALL_TICKERS)} stale" in str(excinfo.value)
    assert "freshest candle 15 min old" in str(excinfo.value)
    assert any("older than" in line for line in top10_live._PROVIDER_DIAGNOSTICS)


# ------------------------------------------------ provider recovery with mock responses


def _recording_providers(monkeypatch, *, batch_results, individual_results=None):
    """Patch the provider calls; return the list of recorded calls."""
    calls: list[tuple[str, dict]] = []
    batches = iter(batch_results)

    def fake_batch(tickers, **kwargs):
        calls.append(("batch", {"tickers": list(tickers), **kwargs}))
        return next(batches)

    def fake_individual(tickers, **kwargs):
        calls.append(("individual", {"tickers": list(tickers), **kwargs}))
        recovered = individual_results or {}
        frames = {t: recovered[t] for t in tickers if t in recovered}
        return frames, [t for t in tickers if t not in frames]

    monkeypatch.setattr(top10_live, "dhan_provider_enabled", lambda: False)
    monkeypatch.setattr(top10_live, "download_symbol_frames", fake_batch)
    monkeypatch.setattr(top10_live, "download_symbols_individually", fake_individual)
    return calls


def _frame_stub() -> pd.DataFrame:
    return pd.DataFrame({"Close": [1.0, 2.0]})


def test_total_batch_failure_triggers_one_small_batch_pass_and_no_individual_storm(
    monkeypatch,
) -> None:
    calls = _recording_providers(
        monkeypatch,
        batch_results=[({}, list(ALL_TICKERS)), ({}, list(ALL_TICKERS))],
    )

    frames, missing, provider = top10_live._download_top10_frames(ALL_TICKERS)

    assert frames == {}
    assert missing == ALL_TICKERS
    assert provider == "Yahoo"
    kinds = [kind for kind, _ in calls]
    assert kinds == ["batch", "batch"]  # no per-symbol requests for a mass failure
    first, second = (call for _, call in calls)
    assert first["batch_size"] == top10_live.TOP10_CHUNK_SIZE
    assert first["recover_missing"] is False
    assert first["retries"] == top10_live.TOP10_PROVIDER_RETRIES
    assert second["batch_size"] == top10_live.TOP10_FALLBACK_CHUNK_SIZE
    assert second["retries"] == 0
    assert second["recover_missing"] is False


def test_partial_batch_failure_recovers_missing_symbols_in_bounded_stages(monkeypatch) -> None:
    resolved = {ticker: _frame_stub() for ticker in ALL_TICKERS[:17]}
    still_missing = ALL_TICKERS[17:]
    recovered_in_small_batch = {still_missing[0]: _frame_stub()}
    calls = _recording_providers(
        monkeypatch,
        batch_results=[
            (resolved, still_missing),
            (recovered_in_small_batch, still_missing[1:]),
        ],
        individual_results={still_missing[1]: _frame_stub()},
    )

    frames, missing, _provider = top10_live._download_top10_frames(ALL_TICKERS)

    assert set(frames) == set(ALL_TICKERS[:17]) | set(still_missing[:2])
    assert missing == [still_missing[2]]
    assert [kind for kind, _ in calls] == ["batch", "batch", "individual"]
    individual = calls[2][1]
    assert individual["tickers"] == still_missing[1:]
    assert individual["retries"] == 0
    assert individual["max_symbols"] == top10_live.TOP10_MAX_SINGLE_SYMBOL_RECOVERY


def test_individual_recovery_is_skipped_when_too_many_symbols_remain(monkeypatch) -> None:
    too_many = ALL_TICKERS[: top10_live.TOP10_MAX_SINGLE_SYMBOL_RECOVERY + 1]
    calls = _recording_providers(
        monkeypatch,
        batch_results=[({}, too_many), ({}, too_many)],
    )

    top10_live._download_top10_frames(too_many)

    assert "individual" not in [kind for kind, _ in calls]


def test_recovery_stops_when_the_scan_time_budget_is_exhausted(monkeypatch) -> None:
    calls = _recording_providers(monkeypatch, batch_results=[({}, ALL_TICKERS[:2])])
    ticks = itertools.count(0, 1000)  # every perf_counter() read is 1000s later
    monkeypatch.setattr(top10_live, "perf_counter", lambda: float(next(ticks)))

    _frames, missing, _provider = top10_live._download_top10_frames(ALL_TICKERS[:2])

    assert missing == ALL_TICKERS[:2]
    assert [kind for kind, _ in calls] == ["batch"]
    assert any("time budget" in line for line in top10_live._PROVIDER_DIAGNOSTICS)


def test_dhan_gaps_fall_back_to_bounded_yahoo_recovery_for_only_those_symbols(
    monkeypatch,
) -> None:
    dhan_frames = {ticker: _frame_stub() for ticker in ALL_TICKERS[:16]}
    dhan_missing = ALL_TICKERS[16:]
    calls = _recording_providers(
        monkeypatch,
        batch_results=[({dhan_missing[0]: _frame_stub()}, dhan_missing[1:])]
        + [({}, dhan_missing[1:])],
    )
    monkeypatch.setattr(top10_live, "dhan_provider_enabled", lambda: True)
    monkeypatch.setattr(
        top10_live,
        "download_dhan_symbol_frames",
        lambda _tickers, **_kw: (dhan_frames, dhan_missing),
    )

    frames, missing, provider = top10_live._download_top10_frames(ALL_TICKERS)

    assert provider == "Dhan + Yahoo fallback"
    assert set(frames) == set(ALL_TICKERS[:16]) | {dhan_missing[0]}
    assert missing == dhan_missing[1:]
    assert calls[0][1]["tickers"] == dhan_missing  # Yahoo is asked only about the gaps
    assert any("Dhan returned no usable data" in d for d in top10_live._PROVIDER_DIAGNOSTICS)


# --------------------------------------------------- refresh state: no loops, no data loss


def test_failed_first_scan_backs_off_exponentially_and_is_capped(
    monkeypatch, executor, clock
) -> None:
    error = top10_live.Top10ScanError("No usable live quotes: test.")
    calls = _scripted_scans(monkeypatch, [error] * 6)
    expected_delays = [15, 30, 60, 60]

    for attempt, delay in enumerate(expected_delays, start=1):
        assert top10_live._start_background_scan(now=clock.current) is True
        executor.run_pending()
        snapshot = top10_live._scan_snapshot(clock.current)
        assert snapshot.failures == attempt
        assert snapshot.running is False
        assert snapshot.last_error == "No usable live quotes: test."
        assert snapshot.result is None
        assert snapshot.next_attempt_at == clock.current + timedelta(seconds=delay)

        # Polling every 2s during the backoff window must not start another scan.
        scans_before = len(calls)
        while clock.current + timedelta(seconds=2) < snapshot.next_attempt_at:
            clock.advance(seconds=2)
            assert top10_live._start_background_scan(now=clock.current) is False
        assert len(calls) == scans_before
        clock.current = snapshot.next_attempt_at

    assert len(calls) == len(expected_delays)


def test_unexpected_provider_exceptions_are_summarised_without_raw_details(
    monkeypatch, executor, clock
) -> None:
    _scripted_scans(monkeypatch, [ValueError("https://secret.example/?token=abc")])

    top10_live._start_background_scan(now=clock.current)
    executor.run_pending()
    snapshot = top10_live._scan_snapshot(clock.current)

    assert snapshot.last_error == "Quote provider error (ValueError)."
    assert "secret" not in (snapshot.last_error or "")


def test_failed_refresh_preserves_the_last_successful_scan(monkeypatch, executor, clock) -> None:
    good = _sample_result(clock.current)
    _scripted_scans(monkeypatch, [good, top10_live.Top10ScanError("provider down")])

    top10_live._start_background_scan(now=clock.current)
    executor.run_pending()
    first = top10_live._scan_snapshot(clock.current)
    assert first.result is good
    assert first.completed_at == clock.current

    clock.advance(seconds=top10_live.TOP10_REFRESH_SECONDS)
    assert top10_live._start_background_scan(now=clock.current) is True
    executor.run_pending()
    second = top10_live._scan_snapshot(clock.current)

    assert second.result is good
    assert second.generation == first.generation
    assert second.completed_at == first.completed_at
    assert second.failures == 1
    assert second.last_error == "provider down"


def test_successful_scan_schedules_the_next_refresh_one_interval_later(
    monkeypatch, executor, clock
) -> None:
    calls = _scripted_scans(monkeypatch, [_sample_result(clock.current)] * 3)

    assert top10_live._start_background_scan(now=clock.current) is True
    executor.run_pending()
    top10_live._scan_snapshot(clock.current)  # settle at the real completion time
    finished_at = clock.current

    clock.advance(seconds=top10_live.TOP10_REFRESH_SECONDS - 1)
    assert top10_live._start_background_scan(now=clock.current) is False
    clock.advance(seconds=1)
    assert top10_live._start_background_scan(now=clock.current) is True
    executor.run_pending()

    assert len(calls) == 2
    assert top10_live._scan_snapshot(clock.current).generation == 2
    assert finished_at < clock.current


def test_only_one_scan_runs_at_a_time(monkeypatch, executor, clock) -> None:
    calls = _scripted_scans(monkeypatch, [_sample_result(clock.current)])

    assert top10_live._start_background_scan(now=clock.current) is True
    for _ in range(5):
        clock.advance(seconds=2)
        assert top10_live._start_background_scan(now=clock.current) is False
        assert top10_live._start_background_scan(now=clock.current, force=True) is False
    assert top10_live._scan_snapshot(clock.current).running is True

    executor.run_pending()
    assert len(calls) == 1


def test_manual_refresh_bypasses_backoff_but_is_rate_limited(monkeypatch, executor, clock) -> None:
    calls = _scripted_scans(
        monkeypatch, [top10_live.Top10ScanError("down"), _sample_result(clock.current)]
    )
    top10_live._start_background_scan(now=clock.current)
    executor.run_pending()
    top10_live._scan_snapshot(clock.current)  # settle the failure; backoff is now active
    assert top10_live._start_background_scan(now=clock.current) is False

    assert top10_live._start_background_scan(now=clock.current, force=True) is False  # too soon
    clock.advance(seconds=top10_live.TOP10_MANUAL_REFRESH_MIN_SECONDS)
    assert top10_live._start_background_scan(now=clock.current, force=True) is True
    executor.run_pending()
    assert len(calls) == 2


def test_a_hung_scan_is_abandoned_instead_of_refreshing_forever(
    monkeypatch, executor, clock
) -> None:
    _scripted_scans(monkeypatch, [_sample_result(clock.current)])
    assert top10_live._start_background_scan(now=clock.current) is True

    clock.advance(seconds=top10_live.TOP10_SCAN_HARD_TIMEOUT_SECONDS - 1)
    assert top10_live._scan_snapshot(clock.current).running is True

    clock.advance(seconds=1)
    snapshot = top10_live._scan_snapshot(clock.current)

    assert snapshot.running is False
    assert snapshot.failures == 1
    assert "timed out" in (snapshot.last_error or "")
    assert snapshot.next_attempt_at is not None and snapshot.next_attempt_at > clock.current
    assert executor.shutdown_calls == 1
    # The orphaned worker finishing late must not be mistaken for a fresh result.
    executor.run_pending()
    assert top10_live._scan_snapshot(clock.current).result is None


def test_session_sync_copies_each_completed_scan_once_and_keeps_its_real_time(
    fake_st, clock
) -> None:
    first = _sample_result(clock.current, symbols=("AAA", "BBB"))
    completed = clock.current
    snapshot = top10_live._ScanSnapshot(first, 1, completed, 0, None, False, None, ())

    top10_live._sync_session_with_snapshot(snapshot)
    clock.advance(seconds=30)
    top10_live._sync_session_with_snapshot(snapshot)  # later polls: nothing new

    assert fake_st.session_state["top10_live_completed_at"] == completed
    assert fake_st.session_state["top10_live_result"] is first
    assert fake_st.session_state["top10_live_previous_result"].empty

    second = _sample_result(clock.current, symbols=("CCC",))
    later = top10_live._ScanSnapshot(second, 2, clock.current, 0, None, False, None, ())
    top10_live._sync_session_with_snapshot(later)

    assert fake_st.session_state["top10_live_result"] is second
    assert fake_st.session_state["top10_live_previous_result"] is first[0]


# --------------------------------------------------------------- rendering: once per page


def _render_poll(fake_st: _FakeStreamlit) -> None:
    fake_st.calls.clear()
    top10_live._render_live_top10_results()


def test_page_renders_controls_once_and_results_contain_no_widgets(
    monkeypatch, executor, clock, fake_st
) -> None:
    _scripted_scans(monkeypatch, [_sample_result(clock.current)])
    monkeypatch.setattr(top10_live, "_live_top10_fragment", top10_live._render_live_top10_results)

    top10_live.show_live_top10_scanner()

    assert len(fake_st.kinds("subheader")) == 1
    assert len(fake_st.kinds("button")) == 1
    assert fake_st.widget_count() == 1  # only the refresh button; nothing in the results

    executor.run_pending()
    for _ in range(3):  # repeated polls re-render the results, never the controls
        _render_poll(fake_st)
        assert fake_st.widget_count() == 0
        assert len(fake_st.kinds("subheader")) == 0
        assert fake_st.top10_tables() == 1


def test_each_poll_emits_exactly_one_status_message_while_first_scan_runs(
    monkeypatch, executor, clock, fake_st
) -> None:
    _scripted_scans(monkeypatch, [_sample_result(clock.current)])

    for _ in range(3):
        _render_poll(fake_st)
        statuses = fake_st.kinds("info") + fake_st.kinds("warning") + fake_st.kinds("error")
        assert len(statuses) == 1
        assert "REFRESHING" in statuses[0]
        assert fake_st.top10_tables() == 0


def test_market_closed_shows_one_message_and_never_scans(
    monkeypatch, executor, clock, fake_st
) -> None:
    clock.current = MARKET_CLOSED
    calls = _scripted_scans(monkeypatch, [])

    for _ in range(3):
        _render_poll(fake_st)
        assert len(fake_st.kinds("info")) == 1
        assert "MARKET CLOSED" in fake_st.kinds("info")[0]
        assert fake_st.kinds("warning") == []
        assert fake_st.kinds("error") == []

    assert calls == []
    assert fake_st.session_state[top10_live.TOP10_SESSION_STATUS_KEY] == "MARKET_CLOSED"


def test_weekends_and_session_edges_are_handled() -> None:
    saturday = datetime(2026, 11, 7, 11, 0, tzinfo=IST)
    assert top10_live._market_is_open(saturday) is False
    assert top10_live._market_is_open(datetime(2026, 11, 5, 9, 14, tzinfo=IST)) is False
    assert top10_live._market_is_open(datetime(2026, 11, 5, 9, 15, tzinfo=IST)) is True
    assert top10_live._market_is_open(datetime(2026, 11, 5, 15, 30, tzinfo=IST)) is True
    assert top10_live._market_is_open(datetime(2026, 11, 5, 15, 31, tzinfo=IST)) is False


def test_market_closed_still_shows_the_last_scan_with_a_stale_warning(
    monkeypatch, executor, clock, fake_st
) -> None:
    _scripted_scans(monkeypatch, [_sample_result(clock.current)])
    _render_poll(fake_st)
    executor.run_pending()
    clock.current = MARKET_CLOSED

    _render_poll(fake_st)

    closed = [text for text in fake_st.kinds("info") if "MARKET CLOSED" in text]
    assert len(closed) == 1
    assert fake_st.top10_tables() == 1
    assert any("stale" in text.lower() for text in fake_st.kinds("warning"))


def test_failed_first_scan_shows_an_actionable_error_not_an_endless_spinner(
    monkeypatch, executor, clock, fake_st
) -> None:
    _scripted_scans(monkeypatch, [top10_live.Top10ScanError("No usable live quotes: 0 of 20.")])
    _render_poll(fake_st)  # starts the scan
    executor.run_pending()

    _render_poll(fake_st)

    statuses = fake_st.kinds("warning") + fake_st.kinds("error")
    assert len(statuses) == 1
    assert "No usable live quotes: 0 of 20." in statuses[0]
    assert "Retrying automatically at" in statuses[0]
    assert not any("Fetching the first" in text for text in fake_st.kinds("info"))
    assert fake_st.top10_tables() == 0


def test_repeated_failures_escalate_to_an_error_and_keep_retrying_slowly(
    monkeypatch, executor, clock, fake_st
) -> None:
    calls = _scripted_scans(monkeypatch, [top10_live.Top10ScanError("down")] * 10)

    for _ in range(40):  # 40 polls, 2s apart, i.e. 80s of an unavailable provider
        _render_poll(fake_st)
        executor.run_pending()
        clock.advance(seconds=top10_live.TOP10_UI_POLL_SECONDS)

    _render_poll(fake_st)
    assert any("LIVE DATA UNAVAILABLE" in text for text in fake_st.kinds("error"))
    # 80s of outage: attempts at ~0s, 15s and 45s, never one per poll.
    assert len(calls) == 3


def test_failed_refresh_keeps_showing_the_last_table(monkeypatch, executor, clock, fake_st) -> None:
    _scripted_scans(monkeypatch, [_sample_result(clock.current), top10_live.Top10ScanError("down")])
    _render_poll(fake_st)
    executor.run_pending()
    _render_poll(fake_st)
    assert fake_st.top10_tables() == 1

    clock.advance(seconds=top10_live.TOP10_REFRESH_SECONDS)
    _render_poll(fake_st)  # starts the refresh that will fail
    executor.run_pending()
    _render_poll(fake_st)

    assert fake_st.top10_tables() == 1
    warnings = fake_st.kinds("warning")
    assert any("Showing the last successful Top-10" in text for text in warnings)


def test_polling_between_refresh_intervals_does_not_start_extra_scans(
    monkeypatch, executor, clock, fake_st
) -> None:
    calls = _scripted_scans(monkeypatch, [_sample_result(clock.current)] * 3)
    _render_poll(fake_st)
    executor.run_pending()

    for _ in range(top10_live.TOP10_REFRESH_SECONDS // top10_live.TOP10_UI_POLL_SECONDS - 1):
        clock.advance(seconds=top10_live.TOP10_UI_POLL_SECONDS)
        _render_poll(fake_st)
        executor.run_pending()
    assert len(calls) == 1

    clock.advance(seconds=top10_live.TOP10_UI_POLL_SECONDS)
    _render_poll(fake_st)
    executor.run_pending()
    assert len(calls) == 2  # the interval elapsed, so exactly one more scan ran


def test_manual_refresh_is_ignored_when_the_market_is_closed(
    monkeypatch, executor, clock, fake_st
) -> None:
    clock.current = MARKET_CLOSED
    calls = _scripted_scans(monkeypatch, [])
    monkeypatch.setattr(top10_live, "_live_top10_fragment", lambda: None)
    fake_st.button_pressed = True

    top10_live.show_live_top10_scanner()

    assert calls == []
    assert executor.pending == []
    assert any("MARKET CLOSED" in text for text in fake_st.kinds("info"))


def test_manual_refresh_during_market_hours_starts_one_scan(
    monkeypatch, executor, clock, fake_st
) -> None:
    _scripted_scans(monkeypatch, [_sample_result(clock.current)])
    monkeypatch.setattr(top10_live, "_live_top10_fragment", lambda: None)
    fake_st.button_pressed = True

    top10_live.show_live_top10_scanner()
    top10_live.show_live_top10_scanner()  # a double click must not queue a second scan

    assert len(executor.pending) == 1
    assert _Cache.cleared >= 1


# ------------------------------------------------------------ structural duplicate guards

ROOT = Path(__file__).resolve().parents[1]


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    return next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _st_calls(node: ast.AST) -> list[str]:
    calls = []
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and isinstance(child.func.value, ast.Name)
            and child.func.value.id == "st"
        ):
            calls.append(child.func.attr)
    return calls


def test_auto_refreshing_fragment_holds_no_widgets_and_one_output_slot() -> None:
    tree = ast.parse((ROOT / "components" / "top10_live.py").read_text(encoding="utf-8"))
    widget_calls = {"button", "selectbox", "number_input", "text_input", "checkbox", "radio"}

    for function_name in ("_render_live_top10_results", "_live_top10_fragment"):
        assert not widget_calls & set(_st_calls(_function(tree, function_name)))

    entry_calls = _st_calls(_function(tree, "show_live_top10_scanner"))
    assert entry_calls.count("button") == 1
    assert entry_calls.count("subheader") == 1
    assert _st_calls(_function(tree, "_live_top10_fragment")).count("empty") == 1


@pytest.mark.parametrize("relative_path", ["app.py", "interfaces/streamlit/app.py"])
def test_each_entry_point_renders_the_scanner_at_most_once(relative_path: str) -> None:
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "show_live_top10_scanner"
    ]
    assert len(calls) <= 1
