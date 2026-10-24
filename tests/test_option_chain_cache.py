"""Tests for the short-lived option-chain cache and .env loading."""

import os

import pandas as pd

from config.env import load_environment
from services import options_analytics as oa


def _result(status: str = "AVAILABLE", spot: float = 24000.0) -> oa.OptionChainResult:
    chain = pd.DataFrame({"strike": [24000.0], "CE LTP": [100.0]})
    return oa.OptionChainResult("NIFTY", "Fake:NIFTY", "2026-10-29", spot, chain, (), status, "")


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def setup_function() -> None:
    oa.clear_option_chain_cache()


def test_repeat_requests_within_ttl_hit_the_provider_once() -> None:
    clock, calls = _Clock(), []

    def fetcher(underlying, expiry):
        calls.append((underlying, expiry))
        return _result()

    first = oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)
    clock.now += oa.AVAILABLE_CACHE_TTL_SECONDS - 1
    second = oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)

    assert len(calls) == 1
    assert first.status == second.status == "AVAILABLE"


def test_cache_expires_and_refetches() -> None:
    clock, calls = _Clock(), []

    def fetcher(underlying, expiry):
        calls.append(1)
        return _result(spot=24000.0 + len(calls))

    oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)
    clock.now += oa.AVAILABLE_CACHE_TTL_SECONDS + 0.1
    refreshed = oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)

    assert len(calls) == 2
    assert refreshed.spot == 24002.0


def test_failures_are_cached_only_briefly() -> None:
    clock, calls = _Clock(), []

    def fetcher(underlying, expiry):
        calls.append(1)
        return _result(status="UNAVAILABLE")

    oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)
    clock.now += oa.UNAVAILABLE_CACHE_TTL_SECONDS - 1
    oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)
    assert len(calls) == 1

    clock.now += 2
    oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)
    assert len(calls) == 2


def test_different_underlyings_and_expiries_are_cached_separately() -> None:
    clock, calls = _Clock(), []

    def fetcher(underlying, expiry):
        calls.append((underlying, expiry))
        return _result()

    for args in [("NIFTY", None), ("BANKNIFTY", None), ("NIFTY", "2026-11-26")]:
        oa.fetch_option_chain_cached(*args, fetcher=fetcher, clock=clock)
        oa.fetch_option_chain_cached(*args, fetcher=fetcher, clock=clock)

    assert calls == [("NIFTY", None), ("BANKNIFTY", None), ("NIFTY", "2026-11-26")]


def test_callers_get_independent_chain_copies() -> None:
    clock = _Clock()

    def fetcher(underlying, expiry):
        return _result()

    first = oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)
    first.chain.loc[0, "CE LTP"] = -1.0
    second = oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)

    assert second.chain.loc[0, "CE LTP"] == 100.0


def test_clear_cache_forces_refetch() -> None:
    clock, calls = _Clock(), []

    def fetcher(underlying, expiry):
        calls.append(1)
        return _result()

    oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)
    oa.clear_option_chain_cache()
    oa.fetch_option_chain_cached("NIFTY", fetcher=fetcher, clock=clock)

    assert len(calls) == 2


def test_load_environment_reads_dotenv_without_overriding_real_variables(
    tmp_path, monkeypatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DHAN_CLIENT_ID=from_file\nDHAN_ACCESS_TOKEN=token_from_file\n")
    monkeypatch.delenv("DHAN_CLIENT_ID", raising=False)
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "real_env_wins")

    assert load_environment(env_file) is True
    assert os.environ["DHAN_CLIENT_ID"] == "from_file"
    assert os.environ["DHAN_ACCESS_TOKEN"] == "real_env_wins"


def test_load_environment_is_a_noop_without_a_file(tmp_path) -> None:
    assert load_environment(tmp_path / "missing.env") is False
