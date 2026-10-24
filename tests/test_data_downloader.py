import pandas as pd

from data import downloader


def _history_frame():
    return pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 13.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 12.0],
            "Volume": [100, 200],
        },
        index=pd.date_range("2026-10-01", periods=2, freq="D"),
    )


def test_download_stock_preserves_explicit_bse_symbol(monkeypatch):
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append((tickers, kwargs))
        return {tickers[0]: _history_frame()}, []

    monkeypatch.setattr(downloader, "download_symbol_frames", fake_download)

    result = downloader.download_stock("500570.BO", period="5d", interval="1d")

    assert calls[0][0] == ["500570.BO"]
    assert calls[0][1]["auto_adjust"] is True
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(result) == 2


def test_download_stock_defaults_unsuffixed_symbol_to_nse(monkeypatch):
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append(tickers)
        return {tickers[0]: _history_frame()}, []

    monkeypatch.setattr(downloader, "download_symbol_frames", fake_download)

    downloader.download_stock("RELIANCE")

    assert calls == [["RELIANCE.NS"]]


def test_download_stock_returns_stable_empty_frame_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        downloader,
        "download_symbol_frames",
        lambda *args, **kwargs: ({}, ["500570.BO"]),
    )

    result = downloader.download_stock("500570.BO")

    assert result.empty
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_download_stock_returns_empty_frame_on_provider_exception(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("network failure")

    monkeypatch.setattr(downloader, "download_symbol_frames", fail)

    result = downloader.download_stock("RELIANCE.NS")

    assert result.empty
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
