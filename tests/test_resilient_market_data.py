from __future__ import annotations

import pandas as pd
import pytest

from services import resilient_market_data as market_data


@pytest.fixture(autouse=True)
def _clear_download_cache():
    from services.cached_download import clear_download_cache

    clear_download_cache()
    yield
    clear_download_cache()


def _frame() -> pd.DataFrame:
    index = pd.date_range("2026-10-05", periods=3, freq="min")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 102.0, 103.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.5, 101.5, 102.5],
            "Volume": [1000, 1100, 1200],
        },
        index=index,
    )


def test_download_symbol_frames_recovers_missing_symbols(monkeypatch) -> None:
    def fake_batch(tickers, **_kwargs):
        return (
            pd.concat(
                {"AAA.NS": _frame()},
                axis=1,
            )
            if "AAA.NS" in tickers
            else pd.DataFrame()
        )

    monkeypatch.setattr(market_data, "_download_batch", fake_batch)
    monkeypatch.setattr(market_data, "_download_single", lambda ticker, **_: _frame())

    frames, missing = market_data.download_symbol_frames(
        ["AAA.NS", "BBB.NS"],
        period="5d",
        interval="1m",
        batch_size=10,
    )

    assert set(frames) == {"AAA.NS", "BBB.NS"}
    assert missing == []


def test_download_market_frames_reports_unresolved_symbols(monkeypatch) -> None:
    monkeypatch.setattr(
        market_data,
        "_download_batch",
        lambda *_args, **_kwargs: pd.DataFrame(),
    )
    monkeypatch.setattr(
        market_data,
        "_download_single",
        lambda *_args, **_kwargs: pd.DataFrame(),
    )

    frames, diagnostics = market_data.download_market_frames(
        ["AAA.NS", "BBB.NS"],
        period="5d",
        interval="1m",
    )

    assert frames == {}
    assert diagnostics["requested"] == 2
    assert diagnostics["usable"] == 0
    assert diagnostics["coverage_pct"] == 0.0
    assert diagnostics["complete"] is False
    assert diagnostics["missing"] == ["AAA.NS", "BBB.NS"]


def test_download_symbol_frames_splits_universe_into_bounded_batches(monkeypatch) -> None:
    batch_calls: list[list[str]] = []

    def fake_batch(tickers, **_kwargs):
        batch_calls.append(list(tickers))
        return pd.concat({ticker: _frame() for ticker in tickers}, axis=1)

    monkeypatch.setattr(market_data, "_download_batch", fake_batch)
    monkeypatch.setattr(
        market_data,
        "_download_single",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("single-symbol recovery should not run when batch data is complete")
        ),
    )

    tickers = [f"STOCK{i}.NS" for i in range(23)]
    frames, missing = market_data.download_symbol_frames(
        tickers,
        period="5y",
        interval="1d",
        batch_size=10,
    )

    assert [len(batch) for batch in batch_calls] == [10, 10, 3]
    assert [ticker for batch in batch_calls for ticker in batch] == tickers
    assert set(frames) == set(tickers)
    assert missing == []


def test_download_symbol_frames_can_report_missing_without_single_recovery(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        market_data,
        "_download_batch",
        lambda *_args, **_kwargs: pd.DataFrame(),
    )
    monkeypatch.setattr(
        market_data,
        "_download_single",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("single-symbol recovery must be disabled")
        ),
    )

    frames, missing = market_data.download_symbol_frames(
        ["AAA.NS", "BBB.NS"],
        period="5y",
        interval="1d",
        recover_missing=False,
    )

    assert frames == {}
    assert missing == ["AAA.NS", "BBB.NS"]


def test_download_market_frames_reports_safe_failure_diagnostics(monkeypatch) -> None:
    monkeypatch.setattr(
        market_data,
        "_download_batch",
        lambda *_args, diagnostics=None, **_kwargs: (
            diagnostics.append("batch request returned no rows")
            if diagnostics is not None
            else None
        )
        or pd.DataFrame(),
    )

    frames, diagnostics = market_data.download_market_frames(
        ["AAA.NS"],
        period="1d",
        interval="1m",
        recover_missing=False,
    )

    assert frames == {}
    assert diagnostics["requested"] == 1
    assert diagnostics["usable"] == 0
    assert diagnostics["missing"] == ["AAA.NS"]
    assert diagnostics["complete"] is False
    assert diagnostics["failure_diagnostics"] == ["batch request returned no rows"]


class _FakeTicker:
    """Stand-in for ``yf.Ticker`` that records how many history requests are made."""

    requests: list[str] = []
    responses: dict[str, pd.DataFrame] = {}

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker

    def history(self, **_kwargs) -> pd.DataFrame:
        type(self).requests.append(self.ticker)
        return type(self).responses.get(self.ticker, pd.DataFrame())


def _install_fake_ticker(monkeypatch, responses: dict[str, pd.DataFrame]) -> list[float]:
    _FakeTicker.requests = []
    _FakeTicker.responses = responses
    sleeps: list[float] = []
    monkeypatch.setattr(market_data.yf, "Ticker", _FakeTicker)
    monkeypatch.setattr(market_data, "sleep", sleeps.append)
    return sleeps


def test_download_single_makes_exactly_one_request_without_retries(monkeypatch) -> None:
    sleeps = _install_fake_ticker(monkeypatch, {})

    frame = market_data._download_single(
        "AAA.NS", period="1d", interval="1m", auto_adjust=False, timeout=4, retries=0
    )

    assert frame.empty
    assert _FakeTicker.requests == ["AAA.NS"]
    assert sleeps == []


def test_download_single_keeps_default_retries_with_backoff(monkeypatch) -> None:
    sleeps = _install_fake_ticker(monkeypatch, {})

    market_data._download_single("AAA.NS", period="1d", interval="1m", auto_adjust=False, timeout=4)

    assert len(_FakeTicker.requests) == market_data.DEFAULT_RETRIES + 1
    assert len(sleeps) == market_data.DEFAULT_RETRIES


def test_download_symbols_individually_recovers_available_symbols(monkeypatch) -> None:
    _install_fake_ticker(monkeypatch, {"BBB.NS": _frame()})

    frames, missing = market_data.download_symbols_individually(
        ["AAA.NS", "BBB.NS", "CCC.NS"], period="1d", interval="1m", retries=0
    )

    assert set(frames) == {"BBB.NS"}
    assert missing == ["AAA.NS", "CCC.NS"]
    assert _FakeTicker.requests == ["AAA.NS", "BBB.NS", "CCC.NS"]


def test_download_symbols_individually_caps_the_number_of_requests(monkeypatch) -> None:
    _install_fake_ticker(monkeypatch, {})
    symbols = [f"S{i}.NS" for i in range(10)]

    frames, missing = market_data.download_symbols_individually(
        symbols, period="1d", interval="1m", retries=0, max_symbols=3
    )

    assert frames == {}
    assert _FakeTicker.requests == symbols[:3]  # hard cap on provider requests
    assert missing == symbols  # unattempted symbols stay unresolved, never invented


def test_download_symbols_individually_never_fabricates_frames(monkeypatch) -> None:
    _install_fake_ticker(monkeypatch, {})

    frames, missing = market_data.download_symbols_individually(
        ["AAA.NS", "AAA.NS", " bbb.ns "], period="1d", interval="1m", retries=0
    )

    assert frames == {}
    assert missing == ["AAA.NS", "BBB.NS"]  # de-duplicated and normalised


def test_batch_then_single_recovery_with_mocked_provider(monkeypatch) -> None:
    """A batch that resolves only some symbols is completed by direct requests."""

    def partial_batch(tickers, **_kwargs):
        return pd.concat({"AAA.NS": _frame()}, axis=1) if "AAA.NS" in tickers else pd.DataFrame()

    monkeypatch.setattr(market_data, "_download_batch", partial_batch)
    _install_fake_ticker(monkeypatch, {"BBB.NS": _frame()})

    frames, missing = market_data.download_symbol_frames(
        ["AAA.NS", "BBB.NS", "CCC.NS"],
        period="1d",
        interval="1m",
        recover_missing=True,
    )

    assert set(frames) == {"AAA.NS", "BBB.NS"}
    assert missing == ["CCC.NS"]


def test_download_symbol_frames_forwards_retry_count_to_single_recovery(monkeypatch) -> None:
    """Fallback requests must honour the caller's retry budget."""
    _install_fake_ticker(monkeypatch, {})

    frames, missing = market_data.download_symbol_frames(
        ["AAA.NS"],
        period="1d",
        interval="1m",
        retries=0,
        recover_missing=True,
    )

    assert frames == {}
    assert missing == ["AAA.NS"]
    assert _FakeTicker.requests == ["AAA.NS"]


def test_download_batch_does_not_enable_hidden_yfinance_retries(monkeypatch) -> None:
    """The wrapper retry budget must remain the only retry layer."""
    network = market_data.yf.config.network
    monkeypatch.setattr(network, "retries", 0)
    monkeypatch.setattr(market_data.yf, "download", lambda **_kwargs: pd.DataFrame())

    market_data._download_batch(
        ["AAA.NS"],
        period="1d",
        interval="1m",
        auto_adjust=False,
        timeout=4,
        retries=0,
    )

    assert network.retries == 0


def test_download_batch_caches_successful_identical_requests(monkeypatch) -> None:
    from services.cached_download import clear_download_cache

    clear_download_cache()
    calls: list[dict[str, object]] = []

    def fake_download(**kwargs):
        calls.append(kwargs)
        return pd.concat({"CACHE_TEST.NS": _frame()}, axis=1)

    monkeypatch.setattr(market_data.yf, "download", fake_download)
    args = {
        "period": "5d",
        "interval": "1d",
        "auto_adjust": False,
        "timeout": 4,
        "retries": 0,
    }

    first = market_data._download_batch(["CACHE_TEST.NS"], **args)
    second = market_data._download_batch(["CACHE_TEST.NS"], **args)

    assert not first.empty
    assert not second.empty
    assert len(calls) == 1


def test_download_batch_does_not_cache_empty_results_and_retries(monkeypatch) -> None:
    from services.cached_download import clear_download_cache

    clear_download_cache()
    calls = 0

    def fake_download(**_kwargs):
        nonlocal calls
        calls += 1
        return pd.DataFrame()

    monkeypatch.setattr(market_data.yf, "download", fake_download)
    monkeypatch.setattr(market_data, "sleep", lambda _seconds: None)

    result = market_data._download_batch(
        ["EMPTY_CACHE_TEST.NS"],
        period="1d",
        interval="1d",
        auto_adjust=False,
        timeout=4,
        retries=2,
    )

    assert result.empty
    assert calls == 3


def test_download_single_caches_successful_identical_requests(monkeypatch) -> None:
    _install_fake_ticker(monkeypatch, {"CACHE_SINGLE.NS": _frame()})

    first = market_data._download_single(
        "CACHE_SINGLE.NS",
        period="5d",
        interval="1d",
        auto_adjust=False,
        timeout=4,
        retries=0,
    )
    second = market_data._download_single(
        "CACHE_SINGLE.NS",
        period="5d",
        interval="1d",
        auto_adjust=False,
        timeout=4,
        retries=0,
    )

    assert not first.empty
    assert not second.empty
    assert _FakeTicker.requests == ["CACHE_SINGLE.NS"]


def test_download_single_uses_separate_cache_entries_for_different_intervals(monkeypatch) -> None:
    _install_fake_ticker(monkeypatch, {"CACHE_INTERVAL.NS": _frame()})

    daily = market_data._download_single(
        "CACHE_INTERVAL.NS",
        period="5d",
        interval="1d",
        auto_adjust=False,
        timeout=4,
        retries=0,
    )
    minute = market_data._download_single(
        "CACHE_INTERVAL.NS",
        period="5d",
        interval="1m",
        auto_adjust=False,
        timeout=4,
        retries=0,
    )

    assert not daily.empty
    assert not minute.empty
    assert _FakeTicker.requests == ["CACHE_INTERVAL.NS", "CACHE_INTERVAL.NS"]
