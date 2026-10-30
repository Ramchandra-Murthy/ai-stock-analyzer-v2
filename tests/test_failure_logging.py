"""Provider failures that used to vanish silently are now logged, with behaviour unchanged."""

import logging
import sys
import types

import pandas as pd
import pytest


def _boom(*args, **kwargs):
    raise RuntimeError("provider down")


@pytest.fixture
def market_scanner(monkeypatch):
    """Import scanner.market_scanner whether or not yfinance is installed."""
    try:
        import yfinance  # noqa: F401
    except ImportError:
        monkeypatch.setitem(sys.modules, "yfinance", types.ModuleType("yfinance"))
    import scanner.market_scanner as module

    monkeypatch.setattr(module.yf, "download", _boom, raising=False)
    return module


@pytest.mark.parametrize("name", ["_download_chunk", "_download_analysis_chunk"])
def test_a_failed_chunk_download_is_logged_and_returns_an_empty_frame(market_scanner, caplog, name):
    with caplog.at_level(logging.DEBUG, logger="scanner.market_scanner"):
        result = getattr(market_scanner, name)(["500325.BO", "532540.BO"])
    assert isinstance(result, pd.DataFrame) and result.empty
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "2 symbols" in warnings[0].getMessage()
    assert "500325.BO" in warnings[0].getMessage()  # names the first symbol
    assert "provider down" in warnings[0].getMessage()
    assert any(r.levelno == logging.DEBUG for r in caplog.records)  # the first attempt too


def test_nse_universe_falls_back_to_the_curated_list_and_says_why(monkeypatch, caplog):
    from scanner import dynamic_universe
    from scanner.universe import NSE_CANDIDATES

    monkeypatch.setattr(dynamic_universe, "_cached_nse_symbols", None)
    monkeypatch.setattr(dynamic_universe, "_download_nse_equity_list", _boom)
    with caplog.at_level(logging.WARNING, logger="scanner.dynamic_universe"):
        symbols = dynamic_universe.dynamic_nse_symbols()
    assert symbols == list(NSE_CANDIDATES)
    assert "NSE equity list download failed" in caplog.text
    assert "provider down" in caplog.text


def _analysis(ticker):
    if ticker.startswith("BAD"):
        raise RuntimeError("no data")
    return {
        "last": {"Close": 100.0, "RSI_14": 55.0, "MACD": 1.2, "ATR": 3.0},
        "signal": {"Score": 70, "Confidence": 0.8, "Recommendation": "HOLD"},
        "trend": {"Trend": "Up"},
    }


def test_watchlist_scan_skips_a_failing_ticker_but_logs_it(monkeypatch, caplog):
    try:
        import services.analyzer  # noqa: F401
    except ImportError:
        stub = types.ModuleType("services.analyzer")
        stub.analyze_stock = _analysis
        monkeypatch.setitem(sys.modules, "services.analyzer", stub)
    import scanner.watchlist_scanner as module

    monkeypatch.setattr(module, "analyze_stock", _analysis)
    with caplog.at_level(logging.WARNING, logger="scanner.watchlist_scanner"):
        frame = module.scan_watchlist(["BAD1", "TCS", "500325.BO"])
    assert list(frame["Symbol"]) == ["TCS", "500325"] or set(frame["Symbol"]) == {"TCS", "500325"}
    assert set(frame["Exchange"]) == {"NSE", "BSE"}
    assert "BAD1.NS" in caplog.text and "no data" in caplog.text


@pytest.fixture
def yfinance_available(monkeypatch):
    """Make ``import yfinance`` work even where the package is not installed."""
    try:
        import yfinance  # noqa: F401
    except ImportError:
        monkeypatch.setitem(sys.modules, "yfinance", types.ModuleType("yfinance"))


def test_price_history_failure_names_the_symbol_and_returns_none(
    yfinance_available, monkeypatch, caplog
):
    import services.technical_service as module

    monkeypatch.setattr(module, "download_symbol_frames", _boom)
    with caplog.at_level(logging.WARNING, logger="services.technical_service"):
        assert module.get_price_history("tcs") is None
    assert "TCS.NS" in caplog.text and "provider down" in caplog.text


def test_price_history_with_no_data_logs_the_symbol(yfinance_available, monkeypatch, caplog):
    import services.technical_service as module

    monkeypatch.setattr(module, "download_symbol_frames", lambda *a, **k: ({}, ["500325.BO"]))
    with caplog.at_level(logging.WARNING, logger="services.technical_service"):
        assert module.get_price_history("500325.BO") is None
    assert "500325.BO" in caplog.text


def test_news_failure_returns_an_empty_list_and_logs(yfinance_available, monkeypatch, caplog):
    import services.news_service as module

    monkeypatch.setattr(module.yf, "Ticker", _boom, raising=False)
    with caplog.at_level(logging.WARNING, logger="services.news_service"):
        assert module.get_company_news("TCS.NS") == []
    assert "News fetch failed" in caplog.text and "provider down" in caplog.text
