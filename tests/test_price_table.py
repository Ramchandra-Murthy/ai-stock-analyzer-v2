import numpy as np
import pandas as pd
import pytest

from services.price_table import load_close_prices, load_returns

IDX = pd.bdate_range("2024-01-01", periods=120)


def _frame(tickers, empty=()):
    rng = np.random.default_rng(0)
    columns = {}
    for t in tickers:
        if t in empty:
            columns[("Close", t)] = np.full(len(IDX), np.nan)
        else:
            columns[("Close", t)] = 100 + rng.normal(0, 1, len(IDX)).cumsum()
    frame = pd.DataFrame(columns, index=IDX)
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)
    return frame


def _fetch(empty=()):
    def fetch(tickers, **kwargs):
        assert kwargs["auto_adjust"] is True
        return _frame(tickers, empty)

    return fetch


NAMES = {"TCS": "TCS.NS", "RELIANCE (BSE 500325)": "500325.BO"}


def test_columns_use_display_names_in_order():
    close, missing = load_close_prices(NAMES, "5y", fetch=_fetch())
    assert list(close.columns) == ["TCS", "RELIANCE (BSE 500325)"]
    assert missing == []


def test_symbol_without_data_is_named_not_fatal():
    close, missing = load_close_prices(
        NAMES, "5y", fetch=_fetch(empty=("500325.BO", "RELIANCE.BO"))
    )
    assert list(close.columns) == ["TCS"]
    assert missing == ["RELIANCE (BSE 500325)"]


def test_single_ticker_flat_frame():
    def fetch(tickers, **kwargs):
        return pd.DataFrame({"Close": np.linspace(10, 20, len(IDX))}, index=IDX)

    close, missing = load_close_prices({"TCS": "TCS.NS"}, "1y", fetch=fetch)
    assert list(close.columns) == ["TCS"] and missing == []


@pytest.mark.parametrize("result", [None, pd.DataFrame()])
def test_empty_download_reports_every_name(result):
    close, missing = load_close_prices(NAMES, "5y", fetch=lambda *a, **k: result)
    assert close.empty and missing == list(NAMES)


def test_load_returns_survives_one_dead_ticker():
    returns, missing = load_returns(NAMES, "5y", fetch=_fetch(empty=("500325.BO", "RELIANCE.BO")))
    assert list(returns.columns) == ["TCS"]
    assert missing == ["RELIANCE (BSE 500325)"]
    assert not returns.isna().any().any()


def test_load_returns_errors_name_the_symbols():
    with pytest.raises(ValueError, match="TCS"):
        load_returns(NAMES, "5y", fetch=lambda *a, **k: None)


def test_load_returns_needs_enough_rows():
    with pytest.raises(ValueError, match="shared trading days"):
        load_returns(NAMES, "5y", fetch=_fetch(), min_rows=500)


def test_duplicate_tickers_and_empty_input_rejected():
    with pytest.raises(ValueError):
        load_close_prices({}, "5y", fetch=_fetch())
    with pytest.raises(ValueError):
        load_close_prices({"A": "TCS.NS", "B": "TCS.NS"}, "5y", fetch=_fetch())


def test_bse_scrip_code_is_requested_by_name_first():
    asked = []

    def fetch(tickers, **kwargs):
        asked.append(list(tickers))
        return _frame(tickers)

    close, missing = load_close_prices(NAMES, "5y", fetch=fetch)
    assert asked == [["TCS.NS", "RELIANCE.BO"]]  # one call, name form
    assert list(close.columns) == ["TCS", "RELIANCE (BSE 500325)"] and missing == []


def test_falls_back_to_scrip_code_when_name_form_is_empty():
    asked = []

    def fetch(tickers, **kwargs):
        asked.append(list(tickers))
        return _frame(tickers, empty=("RELIANCE.BO",))

    close, missing = load_close_prices(NAMES, "5y", fetch=fetch)
    assert asked == [["TCS.NS", "RELIANCE.BO"], ["500325.BO"]]
    assert list(close.columns) == ["TCS", "RELIANCE (BSE 500325)"] and missing == []
