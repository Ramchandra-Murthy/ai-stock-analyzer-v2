from __future__ import annotations

import pandas as pd

from services import resilient_market_data as market_data


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
