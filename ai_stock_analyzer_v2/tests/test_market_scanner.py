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
