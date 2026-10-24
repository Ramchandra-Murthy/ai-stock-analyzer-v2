"""Static wiring checks for the integrated Streamlit app.

These need no third-party packages and no network. They catch the failures that otherwise
only appear when someone clicks a page: a navigation entry that points at a missing file,
or an import of a module/name that no longer exists in the repository.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"
UI_DIRS = ("pages", "modules", "components", "interfaces")


def _first_party_roots() -> set[str]:
    roots = set()
    for path in ROOT.iterdir():
        if path.name.startswith((".", "_")) or path.name in {"tests", "frontend", "docs"}:
            continue
        if path.is_dir() and any(path.rglob("*.py")):
            roots.add(path.name)
        elif path.suffix == ".py":
            roots.add(path.stem)
    return roots


FIRST_PARTY = _first_party_roots()


def _ui_files() -> list[Path]:
    files = [APP]
    for directory in UI_DIRS:
        files.extend(sorted((ROOT / directory).rglob("*.py")))
    return files


def _module_file(dotted: str) -> Path | None:
    base = ROOT.joinpath(*dotted.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    if base.is_dir():  # namespace package (no __init__.py)
        return base
    return None


def _defined_names(path: Path) -> tuple[set[str], bool]:
    """Top-level names a module defines, and whether it has a star import / __getattr__."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    names: set[str] = set()
    dynamic = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            dynamic = True
    for node in tree.body:
        stack = [node]
        while stack:
            current = stack.pop()
            if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                names.add(current.name)
                if current.name == "__getattr__":
                    dynamic = True
            elif isinstance(current, ast.Assign):
                for target in current.targets:
                    names.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
            elif isinstance(current, ast.TypeAlias):  # PEP 695: `type Price = ...`
                names.add(current.name.id)
            elif isinstance(current, ast.AnnAssign | ast.AugAssign):
                names.update(n.id for n in ast.walk(current.target) if isinstance(n, ast.Name))
            elif isinstance(current, ast.Import | ast.ImportFrom):
                names.update((a.asname or a.name).split(".")[0] for a in current.names)
            elif isinstance(current, ast.If | ast.Try | ast.With | ast.For | ast.While):
                for field in ("body", "orelse", "finalbody", "handlers"):
                    for child in getattr(current, field, []):
                        stack.append(child)
                        if isinstance(child, ast.ExceptHandler):
                            stack.extend(child.body)
    return names, dynamic


def test_every_navigation_target_exists() -> None:
    source = APP.read_text(encoding="utf-8")
    pages = set(re.findall(r'"(pages/[A-Za-z0-9_]+\.py)"', source))
    assert pages, "app.py should declare page files"
    missing = sorted(page for page in pages if not (ROOT / page).is_file())
    assert not missing, f"navigation points at missing page files: {missing}"


def test_every_lazy_module_loaded_by_app_exists() -> None:
    source = APP.read_text(encoding="utf-8")
    modules = set(re.findall(r"from ((?:modules|components)\.[a-z_0-9]+) import", source))
    assert modules
    missing = sorted(m for m in modules if _module_file(m) is None)
    assert not missing, f"app.py imports missing modules: {missing}"


def test_every_page_in_pages_folder_is_reachable_or_explicitly_hidden() -> None:
    source = APP.read_text(encoding="utf-8")
    linked = set(re.findall(r'"pages/([A-Za-z0-9_]+\.py)"', source))
    on_disk = {p.name for p in (ROOT / "pages").glob("*.py")}
    # A page that exists but is not in the navigation can never be opened by a user,
    # which is how the options pricing page ended up unreachable.
    allowed_hidden: set[str] = {"Algorithmic_Trading.py"}  # legacy page, superseded by others
    orphans = sorted(on_disk - linked - allowed_hidden)
    assert not orphans, f"pages missing from app.py navigation: {orphans}"


@pytest.mark.parametrize("path", _ui_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_first_party_imports_resolve(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in FIRST_PARTY and _module_file(alias.name) is None:
                    problems.append(f"import {alias.name}: module not found")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            top = node.module.split(".")[0]
            if top not in FIRST_PARTY:
                continue
            target = _module_file(node.module)
            if target is None:
                problems.append(f"from {node.module}: module not found")
                continue
            if target.is_dir():
                continue
            defined, dynamic = _defined_names(target)
            if dynamic:
                continue
            for alias in node.names:
                if alias.name in defined:
                    continue
                if _module_file(f"{node.module}.{alias.name}") is not None:
                    continue  # importing a submodule
                problems.append(f"from {node.module} import {alias.name}: name not defined")
    assert not problems, "\n".join(problems)
