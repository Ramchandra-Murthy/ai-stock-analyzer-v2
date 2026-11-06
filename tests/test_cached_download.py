"""Tests for the shared download cache (no network: the downloader is injected)."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from time import sleep

import pandas as pd
import pytest

from services import cached_download as cd


class FakeDownloader:
    def __init__(self, frame: pd.DataFrame | None = None, error: Exception | None = None) -> None:
        self.calls: list[tuple[object, dict]] = []
        self.frame = pd.DataFrame({"Close": [1.0, 2.0, 3.0]}) if frame is None else frame
        self.error = error

    def __call__(self, tickers, **kwargs):
        self.calls.append((tickers, kwargs))
        if self.error is not None:
            raise self.error
        return self.frame.copy()


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _fresh_cache():
    cd.clear_download_cache()
    yield
    cd.clear_download_cache()


def test_second_call_within_ttl_does_not_download_again() -> None:
    dl, clock = FakeDownloader(), Clock()

    first = cd.cached_download("RELIANCE.NS", period="1y", downloader=dl, clock=clock)
    clock.now += 100
    second = cd.cached_download("RELIANCE.NS", period="1y", downloader=dl, clock=clock)

    assert len(dl.calls) == 1
    pd.testing.assert_frame_equal(first, second)


def test_download_repeats_after_ttl_expires() -> None:
    dl, clock = FakeDownloader(), Clock()

    cd.cached_download("X.NS", period="1y", ttl=60, downloader=dl, clock=clock)
    clock.now += 61
    cd.cached_download("X.NS", period="1y", ttl=60, downloader=dl, clock=clock)

    assert len(dl.calls) == 2


def test_different_period_ticker_or_options_are_separate_entries() -> None:
    dl, clock = FakeDownloader(), Clock()

    cd.cached_download("X.NS", period="1y", downloader=dl, clock=clock)
    cd.cached_download("X.NS", period="5y", downloader=dl, clock=clock)
    cd.cached_download("Y.NS", period="1y", downloader=dl, clock=clock)
    cd.cached_download("X.NS", period="1y", downloader=dl, clock=clock, auto_adjust=True)

    assert len(dl.calls) == 4


def test_ticker_list_order_is_preserved_and_part_of_the_key() -> None:
    dl, clock = FakeDownloader(), Clock()

    cd.cached_download(["A", "B"], period="1y", downloader=dl, clock=clock)
    cd.cached_download(["A", "B"], period="1y", downloader=dl, clock=clock)
    cd.cached_download(["B", "A"], period="1y", downloader=dl, clock=clock)

    assert len(dl.calls) == 2
    assert dl.calls[0][0] == ["A", "B"] and dl.calls[1][0] == ["B", "A"]


def test_arguments_are_forwarded_to_the_downloader() -> None:
    dl = FakeDownloader()

    cd.cached_download(
        ["A"], period="5d", downloader=dl, progress=False, group_by="ticker", threads=False
    )

    assert dl.calls[0][1] == {
        "period": "5d",
        "progress": False,
        "group_by": "ticker",
        "threads": False,
    }


def test_mutating_a_returned_frame_does_not_corrupt_the_cache() -> None:
    dl, clock = FakeDownloader(), Clock()

    fresh = cd.cached_download("X.NS", period="1y", downloader=dl, clock=clock)
    fresh.loc[0, "Close"] = 999.0
    hit = cd.cached_download("X.NS", period="1y", downloader=dl, clock=clock)
    hit.loc[1, "Close"] = 888.0
    again = cd.cached_download("X.NS", period="1y", downloader=dl, clock=clock)

    assert len(dl.calls) == 1
    assert again["Close"].tolist() == [1.0, 2.0, 3.0]


def test_failures_are_not_cached() -> None:
    clock = Clock()
    bad = FakeDownloader(error=RuntimeError("network down"))

    with pytest.raises(RuntimeError):
        cd.cached_download("X.NS", period="1y", downloader=bad, clock=clock)
    good = FakeDownloader()
    result = cd.cached_download("X.NS", period="1y", downloader=good, clock=clock)

    assert len(good.calls) == 1 and not result.empty


def test_empty_results_are_cached_only_briefly() -> None:
    empty, clock = FakeDownloader(frame=pd.DataFrame()), Clock()

    cd.cached_download("X.NS", period="1y", downloader=empty, clock=clock)
    clock.now += cd.EMPTY_TTL_SECONDS - 1
    cd.cached_download("X.NS", period="1y", downloader=empty, clock=clock)
    assert len(empty.calls) == 1

    clock.now += 2
    cd.cached_download("X.NS", period="1y", downloader=empty, clock=clock)
    assert len(empty.calls) == 2


def test_none_from_downloader_is_treated_as_empty() -> None:
    class NoneDownloader(FakeDownloader):
        def __call__(self, tickers, **kwargs):
            self.calls.append((tickers, kwargs))
            return None

    result = cd.cached_download("X.NS", period="1y", downloader=NoneDownloader(), clock=Clock())

    assert result.empty


def test_cache_is_size_bounded_and_evicts_oldest(monkeypatch) -> None:
    monkeypatch.setattr(cd, "MAX_ENTRIES", 5)
    dl, clock = FakeDownloader(), Clock()

    for i in range(12):
        clock.now += 1
        cd.cached_download(f"T{i}", period="1y", downloader=dl, clock=clock)

    assert cd.cache_size() <= 5
    before = len(dl.calls)
    cd.cached_download("T11", period="1y", downloader=dl, clock=clock)
    assert len(dl.calls) == before
    cd.cached_download("T0", period="1y", downloader=dl, clock=clock)
    assert len(dl.calls) == before + 1


def test_expired_entries_are_removed_on_write() -> None:
    dl, clock = FakeDownloader(), Clock()
    cd.cached_download("OLD", period="1y", ttl=10, downloader=dl, clock=clock)

    clock.now += 100
    cd.cached_download("NEW", period="1y", ttl=10, downloader=dl, clock=clock)

    assert cd.cache_size() == 1


def test_identical_concurrent_calls_share_one_download() -> None:
    entered = Event()
    release = Event()
    calls_lock = Lock()
    calls = 0

    def slow_downloader(tickers, **kwargs):
        nonlocal calls
        with calls_lock:
            calls += 1
        entered.set()
        assert release.wait(timeout=5)
        return pd.DataFrame({"Close": [101.0]})

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(cd.cached_download, "X.NS", period="1d", downloader=slow_downloader)
            for _ in range(8)
        ]
        assert entered.wait(timeout=5)
        sleep(0.05)
        release.set()
        results = [future.result(timeout=5) for future in futures]

    assert calls == 1
    assert all(result["Close"].tolist() == [101.0] for result in results)


def test_injected_downloaders_do_not_share_cache_entries() -> None:
    first, second = FakeDownloader(), FakeDownloader()

    cd.cached_download("X.NS", period="1d", downloader=first)
    cd.cached_download("X.NS", period="1d", downloader=second)

    assert len(first.calls) == 1
    assert len(second.calls) == 1


def test_generator_tickers_are_materialized_once() -> None:
    dl = FakeDownloader()
    tickers = (symbol for symbol in ["A.NS", "B.NS"])

    result = cd.cached_download(tickers, period="1d", downloader=dl)

    assert not result.empty
    assert dl.calls[0][0] == ["A.NS", "B.NS"]
