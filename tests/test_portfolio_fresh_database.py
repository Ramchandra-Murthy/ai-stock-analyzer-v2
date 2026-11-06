"""A brand-new database must behave as an empty portfolio, not crash the dashboard."""

import portfolio.portfolio as pf


def test_load_on_fresh_database_returns_empty_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DATABASE", str(tmp_path / "fresh.db"))
    df = pf.load_portfolio()
    assert df.empty
    assert list(df.columns) == ["id", "symbol", "quantity", "buy_price"]


def test_add_update_delete_work_without_prior_setup(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DATABASE", str(tmp_path / "fresh.db"))
    pf.add_stock("TCS.NS", 5, 3500.0)
    row = pf.load_portfolio().iloc[0]
    assert (row["symbol"], row["quantity"]) == ("TCS.NS", 5)
    pf.update_stock(int(row["id"]), 7, 3400.0)
    assert pf.load_portfolio().iloc[0]["quantity"] == 7
    pf.delete_stock(int(row["id"]))
    assert pf.load_portfolio().empty


def test_clear_on_fresh_database_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "DATABASE", str(tmp_path / "fresh.db"))
    pf.clear_portfolio()
