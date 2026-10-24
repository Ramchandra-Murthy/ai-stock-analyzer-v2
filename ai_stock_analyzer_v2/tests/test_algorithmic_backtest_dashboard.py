from pathlib import Path


def test_algorithmic_backtest_page_exists() -> None:
    page = Path("pages/Algorithmic_Backtest.py")
    assert page.exists()
    source = page.read_text(encoding="utf-8")
    assert "backtest_pipeline" in source
    assert "Run backtest" in source
