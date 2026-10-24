"""Tests for the public Fibonacci-Gann helper exports."""

from modules.fibonacci_gann import gann_price_divisions, gann_time_divisions
from modules.fibonacci_gann.gann_divisions import gann_price_divisions as price_impl
from modules.fibonacci_gann.gann_time_divisions import gann_time_divisions as time_impl


def test_gann_price_divisions_is_publicly_exported() -> None:
    assert gann_price_divisions is price_impl
    assert gann_price_divisions(0, 8)[0.5] == 4.0


def test_gann_time_divisions_is_publicly_exported() -> None:
    assert gann_time_divisions is time_impl
    assert gann_time_divisions(0, 80)[0.5] == 40.0
