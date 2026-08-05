"""Both manuscripts must build from a fresh clone.

The burden paper referenced nine figures and the repository tracked none of
them, so anyone cloning it got a paper that would not compile. Nothing caught
that, because it compiles fine in a working tree where the pipeline has been
run. These tests read the dependencies out of the LaTeX and check them against
what git actually tracks.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPERS = (
    REPO_ROOT / "paper" / "portugal_public_debt_interest_report.tex",
    REPO_ROOT / "paper" / "repricing" / "repricing_kernel.tex",
)


def _tracked() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("not a git working tree")
    return set(result.stdout.splitlines())


def _graphics(paper: Path) -> list[str]:
    """Resolve every \\includegraphics target to a repo-relative path."""
    source = paper.read_text(encoding="utf-8")
    targets = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", source)
    resolved = []
    for target in targets:
        path = (paper.parent / target).resolve()
        resolved.append(path.relative_to(REPO_ROOT).as_posix())
    return resolved


@pytest.mark.parametrize("paper", PAPERS, ids=lambda p: p.stem)
def test_every_referenced_figure_is_tracked(paper: Path) -> None:
    if not paper.is_file():
        pytest.skip(f"{paper.name} is not present")
    tracked = _tracked()
    missing = sorted({name for name in _graphics(paper) if name not in tracked})
    assert not missing, (
        f"{paper.name} references figures that git does not track, so it "
        f"cannot build from a clone: {missing}"
    )


@pytest.mark.parametrize("paper", PAPERS, ids=lambda p: p.stem)
def test_every_referenced_figure_exists(paper: Path) -> None:
    if not paper.is_file():
        pytest.skip(f"{paper.name} is not present")
    missing = sorted(
        name for name in _graphics(paper) if not (REPO_ROOT / name).is_file()
    )
    assert not missing, f"{paper.name} references missing files: {missing}"


def test_generated_macros_for_the_repricing_paper_are_tracked() -> None:
    """The repricing paper reads its numbers from a generated file."""
    tracked = _tracked()
    assert "paper/repricing/generated_values.tex" in tracked


def test_figures_are_not_ignored_wholesale() -> None:
    """The PDF exception must survive edits to .gitignore."""
    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "!reports/figures/*.pdf" in ignore
