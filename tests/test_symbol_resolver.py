import pytest

from scanner.universe import BSE_CANDIDATES
from services.symbol_resolver import company_label, resolve_many, resolve_symbol


@pytest.mark.parametrize(
    ("raw", "default", "ticker", "exchange"),
    [
        ("reliance", "NSE", "RELIANCE.NS", "NSE"),
        ("reliance", "BSE", "RELIANCE.BO", "BSE"),
        ("TCS.NS", "BSE", "TCS.NS", "NSE"),  # explicit suffix beats the default
        ("500325.BO", "NSE", "500325.BO", "BSE"),
        ("bse:532540", "NSE", "532540.BO", "BSE"),
        ("NSE:M&M", "BSE", "M&M.NS", "NSE"),
        ("BOM:500325", "NSE", "500325.BO", "BSE"),
        ("500325", "NSE", "500325.BO", "BSE"),  # six digits can only be a BSE scrip code
        ("BAJAJ-AUTO", "NSE", "BAJAJ-AUTO.NS", "NSE"),
        ("  infy.bse ", "NSE", "INFY.BO", "BSE"),
    ],
)
def test_resolve_symbol_accepts_every_common_form(raw, default, ticker, exchange):
    result = resolve_symbol(raw, default)
    assert (result.ticker, result.exchange) == (ticker, exchange)


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "NSE:", "XYZ:TCS", "NSE:TCS.BO", "NSE:500325", "bad symbol!", ".NS", "A" * 30],
)
def test_resolve_symbol_rejects_unusable_input(raw):
    with pytest.raises(ValueError):
        resolve_symbol(raw)


def test_resolve_symbol_rejects_unknown_default_exchange():
    with pytest.raises(ValueError, match="NSE or BSE"):
        resolve_symbol("TCS", "MCX")


def test_resolve_many_dedupes_and_reports_problems_instead_of_dropping_them():
    resolved, problems = resolve_many("tcs, TCS.NS 500325;  bad$symbol\nNSE:500325", "NSE")
    assert [r.ticker for r in resolved] == ["TCS.NS", "500325.BO"]
    assert len(problems) == 2
    assert any("bad$symbol" in p for p in problems)
    assert any("NSE:500325" in p for p in problems)


def test_company_label_names_curated_bse_scrip_codes():
    assert company_label("500325.BO") == "RELIANCE (BSE 500325)"
    assert company_label("532540.BO") == "TCS (BSE 532540)"
    assert company_label("TCS.NS") == "TCS"
    assert company_label("TCS.BO") == "TCS (BSE)"
    assert company_label("not a ticker") == "not a ticker"


def test_every_curated_bse_code_resolves_to_a_labelled_bse_ticker():
    for code in BSE_CANDIDATES:
        item = resolve_symbol(f"{code}.BO")
        assert item.is_bse_scrip_code
        assert company_label(item.ticker).endswith(f"(BSE {code})")
