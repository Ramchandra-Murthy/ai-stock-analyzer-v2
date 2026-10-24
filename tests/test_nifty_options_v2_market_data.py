from datetime import date

import pandas as pd
import pytest

from engine.nifty_options_v2_market_data import select_deepest_itm_call


def test_select_deepest_itm_call_uses_lowest_available_strike() -> None:
    result = select_deepest_itm_call(
        pd.DataFrame(
            {
                "strike": [24800, 24500, 25000],
                "CE LTP": [350, 500, 250],
            }
        ),
        spot=25000,
        expiry=date(2026, 10, 29),
        observed_date=date(2026, 10, 5),
    )

    assert result.contract.strike == 24500
    assert result.observation.ltp == 500


def test_select_deepest_itm_call_rejects_missing_itm_data() -> None:
    with pytest.raises(ValueError, match="no valid ITM CALL quote is available"):
        select_deepest_itm_call(
            pd.DataFrame({"strike": [25000, 25100], "CE LTP": [100, 50]}),
            spot=25000,
            expiry=date(2026, 10, 29),
            observed_date=date(2026, 10, 5),
        )


def test_select_deepest_itm_call_ignores_nan_quote() -> None:
    chain = pd.DataFrame({"strike": [24000.0, 24100.0], "CE LTP": [float("nan"), 150.0]})
    result = select_deepest_itm_call(
        chain,
        spot=25000.0,
        expiry=date(2026, 10, 29),
        observed_date=date(2026, 10, 5),
    )
    assert result.contract.strike == 24100.0
    assert result.observation.ltp == 150.0


def test_select_deepest_itm_call_rejects_all_invalid_quotes() -> None:
    chain = pd.DataFrame({"strike": [24000.0], "CE LTP": [float("nan")]})
    with pytest.raises(ValueError, match="no valid ITM CALL quote is available"):
        select_deepest_itm_call(
            chain,
            spot=25000.0,
            expiry=date(2026, 10, 29),
            observed_date=date(2026, 10, 5),
        )
