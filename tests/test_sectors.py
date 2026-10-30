import pytest

from scanner.sectors import SECTOR_BY_NSE_NAME, UNMAPPED, sector_for_ticker
from scanner.universe import BSE_CANDIDATES, NSE_CANDIDATES


def test_every_universe_stock_has_a_sector_and_nothing_extra():
    assert set(SECTOR_BY_NSE_NAME) == set(NSE_CANDIDATES)


def test_bse_scrip_codes_map_to_the_same_sector_as_their_nse_name():
    for code, name in zip(BSE_CANDIDATES, NSE_CANDIDATES, strict=True):
        assert sector_for_ticker(f"{code}.BO") == SECTOR_BY_NSE_NAME[name]


@pytest.mark.parametrize(
    ("ticker", "sector"),
    [
        ("TCS.NS", "IT services"),
        ("NSE:HDFCBANK", "Banks"),
        ("M&M.NS", "Automobiles"),
        ("BAJAJ-AUTO.NS", "Automobiles"),
        ("RELIANCE.BO", "Oil, gas & energy"),
    ],
)
def test_known_tickers(ticker, sector):
    assert sector_for_ticker(ticker) == sector


@pytest.mark.parametrize("ticker", ["NOTASTOCK.NS", "999999.BO", "bad$", ""])
def test_unknown_or_invalid_tickers_are_unmapped_not_errors(ticker):
    assert sector_for_ticker(ticker) == UNMAPPED
