import pytest

from algorithmic_trading.algorithmic_scanner import _ticker


def test_ticker_uses_exchange_suffix() -> None:
    assert _ticker("RELIANCE", "NSE") == "RELIANCE.NS"
    assert _ticker("500325", "BSE") == "500325.BO"


def test_ticker_does_not_duplicate_matching_suffix() -> None:
    assert _ticker("RELIANCE.NS", "NSE") == "RELIANCE.NS"
    assert _ticker("500325.BO", "BSE") == "500325.BO"


@pytest.mark.parametrize(
    ("symbol", "exchange"),
    [("RELIANCE.NS", "BSE"), ("500325.BO", "NSE")],
)
def test_ticker_rejects_cross_exchange_suffix(symbol: str, exchange: str) -> None:
    with pytest.raises(ValueError, match="different exchange"):
        _ticker(symbol, exchange)


def test_ticker_rejects_unknown_exchange() -> None:
    with pytest.raises(ValueError, match="exchange must be NSE or BSE"):
        _ticker("RELIANCE", "NYSE")
