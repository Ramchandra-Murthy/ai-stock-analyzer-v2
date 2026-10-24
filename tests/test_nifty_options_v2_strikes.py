import pytest

from strategy.nifty_options_v2_strikes import select_deepest_itm_call


def test_selects_deepest_available_itm_strike() -> None:
    assert select_deepest_itm_call([14500, 15000, 15200, 15500], 15300) == 14500


def test_excludes_atm_and_otm_strikes() -> None:
    assert select_deepest_itm_call([15000, 15300, 15500], 15300) == 15000


def test_rejects_when_no_itm_strike_exists() -> None:
    with pytest.raises(ValueError, match="no ITM"):
        select_deepest_itm_call([15300, 15500], 15300)


def test_rejects_invalid_spot() -> None:
    with pytest.raises(ValueError, match="spot"):
        select_deepest_itm_call([14000], 0)
