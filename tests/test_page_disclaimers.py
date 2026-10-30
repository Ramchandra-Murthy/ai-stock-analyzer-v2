"""Every Streamlit page must carry the research disclaimer (or its own equivalent wording)."""

import ast
import pathlib
import re

import pytest

from components.disclaimer import DISCLAIMER_TEXT

PAGES = sorted(pathlib.Path(__file__).resolve().parent.parent.joinpath("pages").glob("*.py"))
OWN_WORDING = re.compile(
    r"not (investment )?advice|research only|educational|not a recommendation|not financial", re.I
)


def _calls_shared_disclaimer(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "show_disclaimer"
        for node in ast.walk(tree)
    )


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_has_a_disclaimer(page):
    source = page.read_text(encoding="utf-8")
    assert _calls_shared_disclaimer(ast.parse(source)) or OWN_WORDING.search(source), (
        f"{page.name} shows no disclaimer: call show_disclaimer() from "
        "components.disclaimer under the page title."
    )


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_shared_disclaimer_is_imported_when_called(page):
    tree = ast.parse(page.read_text(encoding="utf-8"))
    if not _calls_shared_disclaimer(tree):
        pytest.skip("page uses its own wording")
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "components.disclaimer"
        for alias in node.names
    }
    assert "show_disclaimer" in imported


def test_disclaimer_text_makes_the_required_points():
    text = DISCLAIMER_TEXT.lower()
    for phrase in ("investment advice", "past results", "third-party data"):
        assert phrase in text
