"""Regression tests: NSE and BSE instruments must never share a Dhan security ID lookup.

A ``RELIANCE.BO`` ticker used to strip to ``RELIANCE`` and pick up the NSE security ID,
which was then sent to the ``BSE_EQ`` segment (wrong instrument, empty BSE data).
"""

import pandas as pd

from services import dhan_live_provider as provider


def test_bare_key_is_nse_only() -> None:
    mapping = {"RELIANCE": 2885}

    assert provider.resolve_security_id("RELIANCE.NS", mapping) == 2885
    assert provider.resolve_security_id("RELIANCE.BO", mapping) is None


def test_exchange_qualified_keys_are_kept_apart() -> None:
    mapping = {"NSE:RELIANCE": 2885, "BSE:500325": 111111}

    assert provider.resolve_security_id("RELIANCE.NS", mapping) == 2885
    assert provider.resolve_security_id("500325.BO", mapping) == 111111
    # The NSE symbol must not leak into a BSE lookup.
    assert provider.resolve_security_id("RELIANCE.BO", mapping) is None


def test_qualified_key_wins_over_bare_key_for_nse() -> None:
    mapping = {"RELIANCE": 1, "NSE:RELIANCE": 2885}

    assert provider.resolve_security_id("RELIANCE.NS", mapping) == 2885


def test_lookup_is_case_and_whitespace_insensitive() -> None:
    assert provider.resolve_security_id(" tcs.ns ", {"NSE:TCS": 11536}) == 11536


def test_download_uses_bse_segment_only_for_bo_tickers(monkeypatch) -> None:
    calls: list[tuple[int, str]] = []
    candle = {
        "timestamp": [1_760_000_000, 1_760_000_060],
        "open": [1.0, 1.1],
        "high": [1.2, 1.3],
        "low": [0.9, 1.0],
        "close": [1.1, 1.2],
        "volume": [10, 20],
    }

    class FakeClient:
        def intraday_minute_data(self, security_id, segment, *_args, **_kwargs):
            calls.append((security_id, segment))
            return candle

    monkeypatch.setattr(provider, "_security_map", lambda: {"NSE:TCS": 11536, "BSE:532540": 222})
    monkeypatch.setattr(provider, "dhan_provider_enabled", lambda: True)
    monkeypatch.setattr(provider, "DhanMarketData", lambda *a, **k: FakeClient())

    frames, missing = provider.download_dhan_symbol_frames(["TCS.NS", "532540.BO", "INFY.BO"])

    assert set(frames) == {"TCS.NS", "532540.BO"}
    assert all(isinstance(frame, pd.DataFrame) and not frame.empty for frame in frames.values())
    assert missing == ["INFY.BO"]
    assert (11536, "NSE_EQ") in calls
    assert (222, "BSE_EQ") in calls
    assert len(calls) == 2
