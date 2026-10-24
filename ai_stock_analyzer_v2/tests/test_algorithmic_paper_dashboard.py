from pathlib import Path


def test_algorithmic_paper_page_exists() -> None:
    page = Path("pages/Algorithmic_Paper_Trading.py")
    assert page.exists()
    source = page.read_text(encoding="utf-8")
    assert "PaperPortfolio" in source
    assert "Apply signals to paper portfolio" in source
