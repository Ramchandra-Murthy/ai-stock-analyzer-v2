import pandas as pd

from engine.nifty_options_v2_provider_guard import provider_data_ready
from services.options_analytics import OptionChainResult


def _result(*, status: str, spot: float | None, chain: pd.DataFrame) -> OptionChainResult:
    return OptionChainResult(
        underlying="NIFTY",
        provider_symbol="NSE:NIFTY",
        expiry="2026-10-29",
        spot=spot,
        chain=chain,
        expiries=("2026-10-29", "2026-11-26"),
        status=status,
        message="test",
    )


def test_provider_data_ready_requires_available_nonempty_data() -> None:
    chain = pd.DataFrame({"strike": [24000], "CE LTP": [1000]})

    assert provider_data_ready(_result(status="AVAILABLE", spot=25000, chain=chain))


def test_provider_data_ready_rejects_unavailable_provider() -> None:
    chain = pd.DataFrame({"strike": [24000], "CE LTP": [1000]})

    assert not provider_data_ready(_result(status="UNAVAILABLE", spot=25000, chain=chain))


def test_provider_data_ready_rejects_missing_spot() -> None:
    chain = pd.DataFrame({"strike": [24000], "CE LTP": [1000]})

    assert not provider_data_ready(_result(status="AVAILABLE", spot=None, chain=chain))


def test_provider_data_ready_rejects_empty_chain() -> None:
    assert not provider_data_ready(
        _result(
            status="AVAILABLE",
            spot=25000,
            chain=pd.DataFrame(),
        )
    )
