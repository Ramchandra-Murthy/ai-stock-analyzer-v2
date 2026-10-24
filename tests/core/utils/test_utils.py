from __future__ import annotations

from decimal import Decimal

from core.utils import NumberFormatter, get_logger


def test_logger() -> None:
    logger = get_logger("test_logger")
    assert logger is not None


def test_number_formatter() -> None:
    curr_str = NumberFormatter.format_currency(Decimal("125000.50"), "INR")
    assert "125,000.50" in curr_str
    assert "INR" in curr_str

    pct_str = NumberFormatter.format_percentage(Decimal("12.5"))
    assert pct_str == "12.50%"
