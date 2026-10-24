from datetime import date

import pandas as pd
import pytest

from engine.nifty_options_v2_data_validation import validate_expiry, validate_options_frame


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observed_date": ["2021-05-27"],
            "expiry": ["2021-06-24"],
            "strike": [15000],
            "spot": [15300],
            "ltp": [420],
        }
    )


def test_validate_options_frame_normalizes_valid_data() -> None:
    result = validate_options_frame(_frame())

    assert result.loc[0, "observed_date"] == date(2021, 5, 27)
    assert result.loc[0, "expiry"] == date(2021, 6, 24)
    assert result.loc[0, "strike"] == 15000
    assert result.loc[0, "ltp"] == 420


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("strike", 0, "strike and spot must be positive"),
        ("spot", 0, "strike and spot must be positive"),
        ("ltp", -1, "ltp must be non-negative"),
    ],
)
def test_validate_options_frame_rejects_invalid_values(
    column: str, value: float, message: str
) -> None:
    frame = _frame()
    frame.loc[0, column] = value

    with pytest.raises(ValueError, match=message):
        validate_options_frame(frame)


def test_validate_options_frame_rejects_duplicates() -> None:
    frame = pd.concat([_frame(), _frame()], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate"):
        validate_options_frame(frame)


def test_validate_expiry_requires_thursday() -> None:
    validate_expiry(date(2021, 6, 24))

    with pytest.raises(ValueError, match="Thursday"):
        validate_expiry(date(2021, 6, 23))
