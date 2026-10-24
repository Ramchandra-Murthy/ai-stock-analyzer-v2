import pandas as pd
import pytest

from services import research_service, technical_service
from services.market_service import (
    get_latest_available_price,
    get_market_indices,
    normalize_market_symbol,
    scan_market_universe,
)


def test_normalize_nse_symbol():
    assert normalize_market_symbol("RELIANCE", "NSE") == "RELIANCE.NS"


def test_normalize_bse_symbol():
    assert normalize_market_symbol("500570", "BSE") == "500570.BO"


def test_explicit_exchange_suffix_is_preserved():
    assert normalize_market_symbol("TCS.NS", "BSE") == "TCS.NS"
    assert normalize_market_symbol("500570.BO", "NSE") == "500570.BO"


def test_bse_quote_does_not_fall_back_to_another_exchange(monkeypatch):
    calls = []

    def fake_observation(ticker):
        calls.append(ticker)
        return None, None, None, None, "unavailable", False

    monkeypatch.setattr("services.market_service._get_last_observation", fake_observation)

    result = get_latest_available_price("544282", "BSE")

    assert calls == ["544282.BO"]
    assert result["symbol"] == "544282.BO"
    assert result["provider_symbol"] == "544282.BO"
    assert result["exchange"] == "BSE"
    assert result["price"] is None
    assert result["source"] == "Yahoo Finance"


def test_bse_quote_remains_unavailable_without_cross_exchange_substitution(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "services.market_service._get_last_observation",
        lambda ticker: calls.append(ticker) or (None, None, None, None, "unavailable", False),
    )

    result = get_latest_available_price("544282.BO", "BSE")

    assert calls == ["544282.BO"]
    assert result["price"] is None
    assert result["provider_symbol"] == "544282.BO"
    assert result["frequency"] == "unavailable"


def test_scanner_accepts_both_exchanges(monkeypatch):
    def fake_quote(symbol, exchange="NSE"):
        return {
            "symbol": symbol,
            "exchange": "BSE" if symbol.endswith(".BO") else "NSE",
            "price": 100.0,
            "change_pct": 2.0 if symbol.endswith(".NS") else -3.0,
            "observed_at": "2026-09-16T09:00:00",
            "source": "test",
            "frequency": "daily",
            "is_tick_live": False,
            "is_intraday": False,
        }

    monkeypatch.setattr(
        "services.market_service.get_latest_available_price",
        fake_quote,
    )

    result = scan_market_universe(
        {"NSE": ["RELIANCE"], "BSE": ["500570"]},
        top_n=2,
    )

    assert set(result["Exchange"]) == {"NSE", "BSE"}
    assert set(result["Ticker"]) == {"RELIANCE.NS", "500570.BO"}


def test_fast_quote_is_preferred_over_info(monkeypatch):
    class FakeTicker:
        info = {
            "longName": "Test Company",
            "shortName": "TEST",
            "currency": "INR",
        }
        financials = pd.DataFrame()
        balance_sheet = pd.DataFrame()
        dividends = pd.Series(dtype=float)

    monkeypatch.setattr(
        research_service.yf,
        "Ticker",
        lambda symbol: FakeTicker(),
    )
    monkeypatch.setattr(
        research_service,
        "get_latest_available_price",
        lambda symbol: {
            "price": 2510.25,
            "previous_close": 2498.00,
            "source": "yfinance.fast_info",
            "observed_at": "2026-09-12T09:00:00",
            "frequency": "available",
            "is_intraday": True,
            "is_tick_live": False,
        },
    )

    result = research_service.get_stock_profile("TEST")

    assert result["price"] == 2510.25
    assert result["price_source"] == "yfinance.fast_info"
    assert result["previous_close"] == 2498.00
    assert result["market_state"] == "UNKNOWN"


def test_canonical_quote_failure_returns_unavailable_profile(monkeypatch):
    monkeypatch.setattr(
        research_service,
        "get_latest_available_price",
        lambda symbol: {"price": None, "previous_close": None, "source": "unavailable"},
    )

    result = research_service.get_stock_profile("TEST")

    assert result is not None
    assert result["price"] is None
    assert result["price_source"] == "unavailable"


def test_history_boundary_records_provenance(monkeypatch):
    index = pd.date_range("2026-09-01", periods=3, freq="D")
    frame = pd.DataFrame(
        {
            "Open": [1, 2, 3],
            "High": [2, 3, 4],
            "Low": [0, 1, 2],
            "Close": [1.5, 2.5, 3.5],
            "Volume": [100, 200, 300],
        },
        index=index,
    )

    monkeypatch.setattr(
        technical_service,
        "download_symbol_frames",
        lambda *args, **kwargs: ({"TEST.NS": frame}, []),
    )

    result = technical_service.get_price_history("TEST", period="1y")

    assert result is not None
    assert result.attrs["data_source"] == "yfinance.resilient_market_data"
    assert result.attrs["requested_period"] == "1y"
    assert result.attrs["last_bar_timestamp"] == index[-1].isoformat()


def test_history_download_failure_returns_none(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("network failure")

    monkeypatch.setattr(
        technical_service,
        "download_symbol_frames",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network failure")),
    )

    assert technical_service.get_price_history("TEST") is None


def test_quote_exposes_market_session_status(monkeypatch):
    monkeypatch.setattr(
        "services.market_service._get_last_observation",
        lambda ticker: (
            250.0,
            1.5,
            246.31,
            "2026-09-18T11:59:00+05:30",
            "intraday_1m",
            True,
        ),
    )
    monkeypatch.setattr(
        "services.market_service.market_session_status",
        lambda observed_at, frequency: {
            "status": "INTRADAY DATA · TODAY",
            "detail": "Latest candle is recent.",
            "is_current_session": True,
            "is_market_open": True,
        },
    )

    result = get_latest_available_price("RELIANCE", "NSE")

    assert result["session_status"] == "INTRADAY DATA · TODAY"
    assert result["session_detail"] == "Latest candle is recent."
    assert result["is_current_session"] is True
    assert result["is_market_open"] is True


def test_watchlist_movers_preserve_market_session_metadata(monkeypatch):
    def fake_observation(ticker):
        return (
            250.0,
            1.5,
            246.31,
            "2026-10-15T11:59:00+05:30",
            "intraday_1m",
            True,
        )

    monkeypatch.setattr(
        "services.market_service._get_last_observation",
        fake_observation,
    )
    monkeypatch.setattr("services.market_service.get_company_name", lambda ticker: "Test Company")
    monkeypatch.setattr(
        "services.market_service.market_session_status",
        lambda observed_at, frequency: {
            "status": "STALE INTRADAY DATA",
            "detail": "Latest candle is too old.",
            "is_current_session": False,
            "is_market_open": True,
        },
    )

    from services.market_service import get_top_movers

    gainers, losers = get_top_movers({"TEST": "TEST.NS"})

    assert gainers.loc[0, "Session Status"] == "STALE INTRADAY DATA"
    assert gainers.loc[0, "Session Detail"] == "Latest candle is too old."
    assert not gainers.loc[0, "Current Session"]
    assert bool(gainers.loc[0, "Market Open"])
    assert losers.loc[0, "Session Status"] == "STALE INTRADAY DATA"


@pytest.mark.parametrize("top_n", [0, -1, -10])
def test_market_universe_rejects_nonpositive_top_n(top_n):
    with pytest.raises(ValueError, match="top_n must be at least 1"):
        scan_market_universe({}, top_n=top_n)


def test_market_indices_expose_session_detail(monkeypatch):
    monkeypatch.setattr(
        "services.market_service._get_last_observation",
        lambda ticker: (
            25000.0,
            0.5,
            24875.0,
            "2026-10-15T11:59:00+05:30",
            "intraday_1m",
            True,
        ),
    )
    monkeypatch.setattr(
        "services.market_service.market_session_status",
        lambda observed_at, frequency: {
            "status": "DAILY DATA ONLY · INTRADAY UNAVAILABLE",
            "detail": "Latest daily observation is not an intraday quote.",
            "is_current_session": False,
            "is_market_open": True,
        },
    )

    result = get_market_indices()

    assert result
    for index in result.values():
        assert index["session_status"] == "DAILY DATA ONLY · INTRADAY UNAVAILABLE"
        assert index["session_detail"] == "Latest daily observation is not an intraday quote."
        assert index["is_current_session"] is False
        assert index["is_market_open"] is True
