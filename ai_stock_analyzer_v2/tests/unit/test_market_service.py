import pandas as pd

from services import market_service


def test_clean_close_series_handles_multiindex_close():
    frame = pd.DataFrame(
        {
            ("Close", "TEST"): [100.0, 101.0],
            ("Open", "TEST"): [99.0, 100.0],
        }
    )
    close = market_service._clean_close_series(frame)
    assert close.tolist() == [100.0, 101.0]


def test_last_observation_prefers_intraday(monkeypatch):
    def fake_download(tickers, *, interval, **kwargs):
        if interval == "1m":
            return {"TEST": pd.DataFrame({"Close": [100.0, 105.0]})}, []
        return {"TEST": pd.DataFrame({"Close": [99.0, 100.0]})}, []

    monkeypatch.setattr(market_service, "download_symbol_frames", fake_download)

    value, change, previous_close, observed_at, frequency, is_intraday = (
        market_service._get_last_observation("TEST")
    )
    assert value == 105.0
    assert change == 6.06
    assert previous_close == 99.0
    assert frequency == "intraday_1m"
    assert is_intraday is True


def test_last_observation_falls_back_to_daily(monkeypatch):
    def fake_download(tickers, *, interval, **kwargs):
        if interval == "1m":
            return {}, ["TEST"]
        return {"TEST": pd.DataFrame({"Close": [100.0, 105.0]})}, []

    monkeypatch.setattr(market_service, "download_symbol_frames", fake_download)

    value, change, previous_close, observed_at, frequency, is_intraday = (
        market_service._get_last_observation("TEST")
    )
    assert value == 105.0
    assert change == 5.0
    assert previous_close == 100.0
    assert frequency == "daily"
    assert is_intraday is False


def test_last_observation_rejects_empty_provider_data(monkeypatch):
    def fake_download(tickers, *, interval, **kwargs):
        return {}, ["TEST"]

    monkeypatch.setattr(market_service, "download_symbol_frames", fake_download)

    assert market_service._get_last_observation("TEST") == (
        None,
        None,
        None,
        None,
        "unavailable",
        False,
    )


def test_indices_keep_all_expected_keys(monkeypatch):
    def fake_observation(ticker):
        return (100.0, 1.0, 99.0, "2026-09-08T10:00:00", "intraday_1m", True)

    monkeypatch.setattr(market_service, "_get_last_observation", fake_observation)
    monkeypatch.setattr(
        market_service,
        "market_session_status",
        lambda observed_at, frequency: {
            "status": "INTRADAY DATA · TODAY",
            "is_current_session": True,
            "is_market_open": True,
            "detail": "test",
        },
    )

    data = market_service.get_market_indices()

    assert set(data) == set(market_service.MARKET_INDICES)
    assert all(item["frequency"] == "intraday_1m" for item in data.values())
    assert all(item["is_intraday"] is True for item in data.values())
    assert all(item["session_status"] == "INTRADAY DATA · TODAY" for item in data.values())
    assert all(item["is_current_session"] is True for item in data.values())
    assert all(item["is_market_open"] is True for item in data.values())


def test_normalize_market_symbol_rejects_unknown_exchange():
    import pytest

    with pytest.raises(ValueError, match="exchange must be NSE or BSE"):
        market_service.normalize_market_symbol("RELIANCE", "NYSE")


def test_normalize_market_symbol_preserves_explicit_exchange_suffix():
    assert market_service.normalize_market_symbol("RELIANCE.NS", "BSE") == "RELIANCE.NS"
    assert market_service.normalize_market_symbol("500325.BO", "NSE") == "500325.BO"
