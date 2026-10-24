from pathlib import Path


def test_algorithmic_dashboard_page_exists() -> None:
    page = Path("pages/Algorithmic_Trading.py")
    assert page.exists()
    source = page.read_text(encoding="utf-8")
    assert "analyze_symbol" in source
    assert "Run algorithmic analysis" in source
