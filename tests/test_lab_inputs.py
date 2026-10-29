import pytest

from algorithmic_trading.lab_inputs import parse_holdings, parse_views


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
