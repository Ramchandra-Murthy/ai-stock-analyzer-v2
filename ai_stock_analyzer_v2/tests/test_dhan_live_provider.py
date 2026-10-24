from __future__ import annotations

import json

import pandas as pd

from services import dhan_live_provider


def test_security_map_ignores_invalid_entries(monkeypatch):
    monkeypatch.setenv(
        "DHAN_SECURITY_MAP_JSON",
        json.dumps({"RELIANCE": 2885, "BAD": "not-an-id", "TCS": "11536"}),
    )

    assert dhan_live_provider._security_map() == {"RELIANCE": 2885, "TCS": 11536}


def test_response_frame_converts_dhan_columns():
    response = {
        "data": {
            "timestamp": [1_700_000_000, 1_700_000_060],
            "open": [100, 101],
            "high": [102, 103],
            "low": [99, 100],
            "close": [101, 102],
            "volume": [1000, 1200],
        }
    }

    frame = dhan_live_provider._response_frame(response)

    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(frame) == 2
    assert float(frame["Close"].iloc[-1]) == 102
    assert isinstance(frame.index, pd.DatetimeIndex)


def test_provider_is_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("DHAN_CLIENT_ID", raising=False)
    monkeypatch.delenv("DHAN_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("DHAN_SECURITY_MAP_JSON", json.dumps({"RELIANCE": 2885}))

    assert dhan_live_provider.dhan_provider_enabled() is False
