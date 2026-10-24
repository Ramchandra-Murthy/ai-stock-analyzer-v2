from services.sector_mapping import sector_for_symbol


def test_sector_for_known_symbol():
    assert sector_for_symbol("RELIANCE") == "Energy"
    assert sector_for_symbol("hdfcbank") == "Financials"
    assert sector_for_symbol("CHENNPETRO") == "Energy"
    assert sector_for_symbol("DHANBANK") == "Financials"
    assert sector_for_symbol("NELCAST") == "Metals"
    assert sector_for_symbol("PNGSREVA") == "Consumer"
    assert sector_for_symbol("INDIAGLYCO") == "Chemicals"


def test_sector_for_unknown_symbol_is_unclassified():
    assert sector_for_symbol("NOT_A_REAL_SYMBOL") == "Unclassified"
