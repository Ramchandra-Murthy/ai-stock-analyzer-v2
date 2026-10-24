from __future__ import annotations

import pytest

from core.identifiers import ISIN, CompanySymbol


def test_identifiers_creation() -> None:
    isin = ISIN("US0378331005")
    assert isin.code == "US0378331005"

    sym = CompanySymbol("AAPL")
    assert sym.value == "AAPL"


def test_isin_invalid() -> None:
    with pytest.raises(ValueError):
        ISIN("INVALID")
