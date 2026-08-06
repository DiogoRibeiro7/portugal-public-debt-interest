"""Every third-party import must be a declared dependency.

Twice in one release cycle a package was imported by the source, installed on
the development machine, and never declared: PyYAML's type stubs, then
statsmodels. Both passed locally and could not pass anywhere else, which is the
worst shape a defect can take -- the local run is not evidence.

The check maps import names to distribution names through the installed
environment, so ``yaml`` resolves to ``PyYAML`` rather than being compared as a
string.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
PYPROJECT = REPO_ROOT / "pyproject.toml"

#: Packages defined in this repository.
FIRST_PARTY = {"pt_debt", "pt_debt_interest"}


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        # A relative import has no module of its own to declare.
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def _imported_third_party() -> set[str]:
    imports: set[str] = set()
    for module in sorted(SRC.rglob("*.py")):
        imports |= _top_level_imports(module)
    return {
        name
        for name in imports
        if name not in FIRST_PARTY and name not in sys.stdlib_module_names
    }


def _declared_distributions() -> set[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    declared: set[str] = set()
    for spec in data.get("project", {}).get("dependencies", []):
        # "pandas>=2.1,<3.0" -> "pandas"
        name = spec.split(";")[0].strip()
        for separator in ("[", ">", "<", "=", "!", "~", " "):
            name = name.split(separator)[0]
        declared.add(name.strip().lower().replace("_", "-"))
    return declared


def _distribution_for(import_name: str) -> set[str]:
    mapping = packages_distributions()
    return {dist.lower().replace("_", "-") for dist in mapping.get(import_name, [])}


def test_source_tree_is_scannable() -> None:
    """A silent zero here would make every other assertion vacuous."""
    assert SRC.is_dir()
    assert len(list(SRC.rglob("*.py"))) > 10
    assert _imported_third_party(), "no third-party imports found; the scan is broken"


@pytest.mark.parametrize("import_name", sorted(_imported_third_party()))
def test_third_party_import_is_declared(import_name: str) -> None:
    distributions = _distribution_for(import_name)
    if not distributions:
        pytest.skip(f"{import_name} is not installed; cannot resolve its distribution")
    declared = _declared_distributions()
    assert distributions & declared, (
        f"`import {import_name}` resolves to {sorted(distributions)}, none of "
        f"which is declared in pyproject.toml [project.dependencies]. It works "
        f"here only because it is already installed."
    )


def test_the_two_dependency_lists_agree() -> None:
    """Poetry and PEP 621 both declare runtime dependencies; they must match."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    poetry = {
        name.lower().replace("_", "-")
        for name in data["tool"]["poetry"]["dependencies"]
        if name != "python"
    }
    assert poetry == _declared_distributions(), (
        "[tool.poetry.dependencies] and [project.dependencies] disagree: "
        f"only in poetry {sorted(poetry - _declared_distributions())}, "
        f"only in project {sorted(_declared_distributions() - poetry)}"
    )
