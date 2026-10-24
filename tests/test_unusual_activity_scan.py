"""Regression tests for the unusual-activity scanner.

``scan_unusual_activity`` used to check an undefined ``history`` variable left
over from an older download API, raising ``NameError`` whenever market data
was actually returned.
"""

import pandas as pd
import pytest

pytest.importorskip("yfinance")  # the scanner's import chain needs the market-data stack

from scanner import unusual_activity  # noqa: E402


def _two_session_frame(latest_volume: float, latest_close: float) -> pd.DataFrame:
    """Five-minute bars for a prior session and the current session."""
    previous = pd.date_range("2026-10-15 09:15", periods=4, freq="5min")
    current = pd.date_range("2026-10-16 09:15", periods=4, freq="5min")
    index = previous.append(current)
    return pd.DataFrame(
        {
            "Open": [100.0] * 8,
            "High": [106.0] * 8,
            "Low": [99.0] * 8,
            "Close": [100.0] * 7 + [latest_close],
            "Volume": [100.0] * 7 + [latest_volume],
        },
        index=index,
    )


def _fake_download(frame_for_each_ticker: pd.DataFrame | None):
    def fake(tickers, **_kwargs):
        frames = (
            {ticker: frame_for_each_ticker.copy() for ticker in tickers}
            if frame_for_each_ticker is not None
            else {}
        )
        return frames, {"missing": [] if frames else list(tickers)}

    return fake


def test_scan_returns_rows_when_data_is_available(monkeypatch) -> None:
    monkeypatch.setattr(
        unusual_activity,
        "download_market_frames",
        _fake_download(_two_session_frame(latest_volume=1000.0, latest_close=105.0)),
    )

    result = unusual_activity.scan_unusual_activity(
        limit=5, cap_category="Large cap", exchange_category="NSE"
    )

    assert not result.empty
    assert len(result) <= 5
    assert (result["Relative volume"] >= 1.5).all()
    assert (result["Session change %"] > 0).all()
    assert result.attrs["scan_stats"]["usable_count"] > 0


def test_scan_skips_symbols_without_a_volume_spike(monkeypatch) -> None:
    monkeypatch.setattr(
        unusual_activity,
        "download_market_frames",
        _fake_download(_two_session_frame(latest_volume=100.0, latest_close=105.0)),
    )

    result = unusual_activity.scan_unusual_activity(
        limit=5, cap_category="Large cap", exchange_category="NSE"
    )

    assert result.empty


def test_scan_handles_empty_download_without_raising(monkeypatch) -> None:
    monkeypatch.setattr(unusual_activity, "download_market_frames", _fake_download(None))

    result = unusual_activity.scan_unusual_activity(
        limit=5, cap_category="Large cap", exchange_category="NSE"
    )

    assert result.empty
    assert result.attrs["scan_stats"]["empty_chunks"] > 0
