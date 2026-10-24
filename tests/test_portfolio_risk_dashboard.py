from pathlib import Path


def test_portfolio_risk_page_exists() -> None:
    page = Path("pages/Portfolio_Risk_Allocation.py")
    assert page.exists()
    source = page.read_text(encoding="utf-8")
    assert "PortfolioLimits" in source
    assert "Calculate portfolio allocation" in source
