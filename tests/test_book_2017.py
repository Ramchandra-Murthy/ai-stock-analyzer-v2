# ruff: noqa: I001

"""Golden-reference tests for the book published 2017 NIFTY CALL table."""

from __future__ import annotations

import pandas as pd
import pytest

from engine.backtest_engine import BacktestEngine
from strategy.book_v1 import BookV1Strategy

BOOK_2017 = [
    ("2017-01", 8103, 8602, 7500, 623, 1092),
    ("2017-02", 8602, 8939, 8000, 616, 940),
    ("2017-03", 8939, 9173, 8400, 560, 774),
    ("2017-04", 9173, 9342, 8500, 678, 842),
    ("2017-05", 9342, 9509, 8800, 545, 702),
    ("2017-06", 9509, 9504, 9000, 500, 501),
    ("2017-07", 9504, 10020, 9000, 522, 1018),
    ("2017-08", 10020, 9917, 9500, 574, 410),
    ("2017-09", 9917, 9768, 9400, 545, 364),
    ("2017-10", 9768, 10343, 9200, 593, 1143),
    ("2017-11", 10343, 10226, 9800, 573, 422),
    ("2017-12", 10226, 10477, 9600, 682, 881),
]


def _book_2017_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "entry_date": pd.Timestamp(f"{month}-01"),
                "exit_date": pd.Timestamp(f"{month}-28"),
                "spot_entry": spot_entry,
                "spot_exit": spot_exit,
                "strike": strike,
                "entry_ltp": entry_ltp,
                "exit_ltp": exit_ltp,
                "lot_size": 75,
            }
            for month, spot_entry, spot_exit, strike, entry_ltp, exit_ltp in BOOK_2017
        ]
    )


def test_2017_matches_book_totals() -> None:
    result = BacktestEngine(BookV1Strategy()).run(_book_2017_dataframe())

    assert len(result) == 12
    assert result["points_pnl"].sum() == pytest.approx(2078)
    assert result["gross_pnl"].sum() == pytest.approx(155850)


def test_2017_matches_book_win_loss_counts() -> None:
    result = BacktestEngine(BookV1Strategy()).run(_book_2017_dataframe())

    assert (result["points_pnl"] > 0).sum() == 9
    assert (result["points_pnl"] < 0).sum() == 3
    assert (result["exit_ltp"] == 0).sum() == 0
