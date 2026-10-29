import pytest

from algorithmic_trading.lab_inputs import parse_holdings, parse_views, resolve_holdings


def test_parse_holdings_normalises_case_and_separators():
    assert parse_holdings("tcs 30\nInfy, 20\n\n") == {"TCS": 30.0, "INFY": 20.0}


@pytest.mark.parametrize(
    "raw",
    ["", "   \n", "TCS", "TCS abc", "TCS -5", "TCS 10\nTCS 20", "TCS 1 2"],
)
def test_parse_holdings_rejects_bad_input(raw):
    with pytest.raises(ValueError):
        parse_holdings(raw)


def test_parse_views_absolute_and_relative():
    views = parse_views("tcs 0.15 0.6\nTCS>infy 0.03 0.5")
    assert views[0].weights == {"TCS": 1.0}
    assert views[0].expected_return == pytest.approx(0.15)
    assert views[0].confidence == pytest.approx(0.6)
    assert views[1].weights == {"TCS": 1.0, "INFY": -1.0}


def test_parse_views_blank_is_empty():
    assert parse_views("\n  \n") == []


@pytest.mark.parametrize(
    "raw",
    ["TCS 0.1", "TCS x 0.5", "TCS 0.1 1.0", "TCS 0.1 0", "TCS>TCS 0.1 0.5", ">INFY 0.1 0.5"],
)
def test_parse_views_rejects_bad_input(raw):
    with pytest.raises(ValueError):
        parse_views(raw)


def test_resolve_holdings_supports_bse_codes_and_keeps_listings_distinct():
    tickers, weights = resolve_holdings({"TCS": 30, "500325": 20, "BSE:TCS": 10, "NSE:ITC": 5})
    assert tickers == {
        "TCS": "TCS.NS",
        "RELIANCE (BSE 500325)": "500325.BO",
        "TCS (BSE)": "TCS.BO",
        "ITC": "ITC.NS",
    }
    assert weights["RELIANCE (BSE 500325)"] == 20


def test_resolve_holdings_uses_the_default_exchange_for_bare_names():
    tickers, _ = resolve_holdings({"INFY": 1}, "BSE")
    assert tickers == {"INFY (BSE)": "INFY.BO"}


@pytest.mark.parametrize("holdings", [{"TCS": 1, "TCS.NS": 2}, {"500325": 1, "BSE:500325": 1}])
def test_resolve_holdings_rejects_the_same_security_twice(holdings):
    with pytest.raises(ValueError, match="same security"):
        resolve_holdings(holdings)


def test_resolve_holdings_rejects_unusable_symbols():
    with pytest.raises(ValueError):
        resolve_holdings({"bad$": 1})


def test_parse_views_use_the_same_labels_as_resolved_holdings():
    tickers, _ = resolve_holdings({"500325": 1, "TCS": 1, "BSE:INFY": 1})
    views = parse_views("500325>tcs 0.02 0.5\nBSE:INFY 0.1 0.4")
    for view in views:
        assert set(view.weights) <= set(tickers)
    assert views[0].weights == {"RELIANCE (BSE 500325)": 1.0, "TCS": -1.0}


def test_parse_views_default_exchange_applies_to_bare_names():
    assert parse_views("INFY 0.1 0.5", "BSE")[0].weights == {"INFY (BSE)": 1.0}


def test_parse_views_reject_the_same_security_written_two_ways():
    with pytest.raises(ValueError):
        parse_views("TCS>TCS.NS 0.01 0.5")


from algorithmic_trading.lab_inputs import parse_share_counts  # noqa: E402

ALLOWED = {"TCS", "RELIANCE (BSE 500325)"}


def test_share_counts_blank_means_nothing_held():
    assert parse_share_counts("  \n", "NSE", ALLOWED) == {}


def test_share_counts_resolve_bse_codes_and_whole_numbers():
    got = parse_share_counts("tcs 10\n500325 5", "NSE", ALLOWED)
    assert got == {"TCS": 10, "RELIANCE (BSE 500325)": 5}


@pytest.mark.parametrize("raw", ["TCS 1.5", "INFY 3", "TCS -2", "TCS 10\nTCS.NS 5"])
def test_share_counts_reject_bad_input(raw):
    with pytest.raises(ValueError):
        parse_share_counts(raw, "NSE", ALLOWED)
