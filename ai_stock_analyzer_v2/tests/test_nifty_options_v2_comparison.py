import pytest

from engine.nifty_options_v2_comparison import (
    BookSeriesResult,
    compare_series,
    total_points,
)


def test_compare_series_reports_actual_minus_book_points() -> None:
    book = [
        BookSeriesResult("2017-01", 469),
        BookSeriesResult("2017-02", 324),
    ]
    actual = [
        BookSeriesResult("2017-01", 450),
        BookSeriesResult("2017-02", 350),
    ]

    result = compare_series(book, actual)

    assert [(row.series, row.difference_points) for row in result] == [
        ("2017-01", -19),
        ("2017-02", 26),
    ]


def test_compare_series_rejects_missing_series() -> None:
    with pytest.raises(ValueError, match="series sets differ"):
        compare_series(
            [BookSeriesResult("2017-01", 469)],
            [BookSeriesResult("2017-02", 324)],
        )


def test_total_points() -> None:
    assert total_points([BookSeriesResult("2017-01", 469), BookSeriesResult("2017-02", 324)]) == 793
