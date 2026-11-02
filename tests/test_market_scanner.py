import pandas as pd

from scanner.market_scanner import _extract_series


def test_extract_series_supports_ticker_first_columns() -> None:
    columns = pd.MultiIndex.from_product([["RELIANCE.NS"], ["Close", "Volume"]])
    frame = pd.DataFrame([[100.0, 1_000_000]], columns=columns)

    assert _extract_series(frame, "RELIANCE.NS", "Close").tolist() == [100.0]


def test_extract_series_supports_field_first_columns() -> None:
    columns = pd.MultiIndex.from_product([["Close", "Volume"], ["RELIANCE.NS"]])
    frame = pd.DataFrame([[100.0, 1_000_000]], columns=columns)

    assert _extract_series(frame, "RELIANCE.NS", "Volume").tolist() == [1_000_000]


def test_market_scan_uses_only_requested_exchange(monkeypatch) -> None:
    from scanner import market_scanner

    calls = []
    monkeypatch.setattr(market_scanner, "merge_nse_universe", lambda: ["RELIANCE"])
    monkeypatch.setattr(market_scanner, "merge_bse_universe", lambda: ["500325"])
    monkeypatch.setattr(
        market_scanner,
        "_batch_change_screen",
        lambda candidates: calls.append(candidates) or [],
    )

    result = market_scanner.market_scan("BSE")

    assert result.empty
    assert calls == [{"BSE": ["500325"]}]


def test_market_scan_includes_both_exchanges_by_default(monkeypatch) -> None:
    from scanner import market_scanner

    calls = []
    monkeypatch.setattr(market_scanner, "merge_nse_universe", lambda: ["RELIANCE"])
    monkeypatch.setattr(market_scanner, "merge_bse_universe", lambda: ["500325"])
    monkeypatch.setattr(
        market_scanner,
        "_batch_change_screen",
        lambda candidates: calls.append(candidates) or [],
    )

    result = market_scanner.market_scan()

    assert result.empty
    assert calls == [{"NSE": ["RELIANCE"], "BSE": ["500325"]}]


def test_bse_candidates_follow_selected_nse_cap_basket() -> None:
    from scanner.universe import bse_candidates_for_nse_symbols

    selected = {"RELIANCE", "TCS", "NOT_IN_CURATED_UNIVERSE"}

    assert bse_candidates_for_nse_symbols(selected) == ["500325", "532540"]


def test_day_trader_cap_filter_includes_bse_candidates() -> None:
    from scanner.day_trader_opportunity import select_day_trader_universe

    selected = select_day_trader_universe("Large cap", "BSE")

    assert ("500325", "BSE") in selected
    assert ("532540", "BSE") in selected
    assert all(exchange == "BSE" for _symbol, exchange in selected)


def test_market_scan_reports_per_exchange_coverage_when_no_movers(monkeypatch) -> None:
    from scanner import market_scanner

    monkeypatch.setattr(market_scanner, "merge_nse_universe", lambda: ["RELIANCE"])
    monkeypatch.setattr(market_scanner, "merge_bse_universe", lambda: ["500325"])
    monkeypatch.setattr(market_scanner, "_batch_change_screen", lambda candidates: [])

    result = market_scanner.market_scan("BSE")

    assert result.empty
    assert result.attrs["scanner_coverage"] == {
        "BSE": {
            "candidates": 1,
            "tickers_requested": 1,
            "histories_returned": 0,
            "histories_rejected": 1,
            "analyses_completed": 0,
            "final_rows": 0,
        }
    }


def test_batch_change_screen_excludes_ticker_with_stale_last_bar(monkeypatch) -> None:
    """A halted name (old last bar, big old move) must not rank beside fresh tickers."""
    import pandas as pd

    from scanner import market_scanner

    dates = pd.to_datetime(["2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"])
    nan = float("nan")
    columns = pd.MultiIndex.from_product([["AAA.NS", "BBB.NS"], ["Close", "Volume"]])
    history = pd.DataFrame(
        [
            [100.0, 1_000, 100.0, 1_000],
            [100.0, 1_000, 150.0, 1_000],  # BBB: +50% on 10-28, then no more bars
            [100.0, 1_000, nan, nan],
            [110.0, 1_000, nan, nan],  # AAA: +10% on the latest session
        ],
        index=dates,
        columns=columns,
    )
    monkeypatch.setattr(market_scanner, "_download_chunk", lambda chunk: history)

    ranked = market_scanner._batch_change_screen({"NSE": ["AAA", "BBB"]})

    assert [row[0] for row in ranked] == ["AAA.NS"]
    assert round(ranked[0][2], 6) == 10.0


def test_batch_change_screen_keeps_all_tickers_on_the_same_session(monkeypatch) -> None:
    import pandas as pd

    from scanner import market_scanner

    dates = pd.to_datetime(["2026-10-29", "2026-10-30"])
    columns = pd.MultiIndex.from_product([["AAA.NS", "BBB.NS"], ["Close", "Volume"]])
    history = pd.DataFrame(
        [[100.0, 1_000, 100.0, 1_000], [110.0, 1_000, 80.0, 1_000]],
        index=dates,
        columns=columns,
    )
    monkeypatch.setattr(market_scanner, "_download_chunk", lambda chunk: history)

    ranked = market_scanner._batch_change_screen({"NSE": ["AAA", "BBB"]})

    assert sorted(row[0] for row in ranked) == ["AAA.NS", "BBB.NS"]
    assert ranked[0][0] == "BBB.NS"  # |-20%| outranks |+10%|


def test_analyze_history_stamps_the_last_bar_date() -> None:
    import numpy as np
    import pandas as pd

    from scanner import market_scanner

    index = pd.bdate_range(end="2026-10-30", periods=120)
    close = pd.Series(np.linspace(100, 130, len(index)), index=index)
    history = pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 1_000_000,
        }
    )

    row = market_scanner._analyze_history("AAA.NS", history, 1.0e8)

    assert row is not None
    assert row["Data As Of"] == "2026-10-30"
