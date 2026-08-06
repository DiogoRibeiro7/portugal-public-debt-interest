"""The manuscript quotes no number it did not generate.

These tests exist because the failure they guard against is silent: a result
typed into the LaTeX body keeps compiling long after the pipeline that produced
it has moved on, and the paper then reports a number no artefact supports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pt_debt.repricing.manuscript import (
    MACRO_FILENAME,
    undefined_macros,
    verify_manuscript_values,
)
from pt_debt_interest.exceptions import ValidationError

PAPER_DIR = Path("paper/repricing")
TEX_PATH = PAPER_DIR / "repricing_kernel.tex"
MACRO_PATH = PAPER_DIR / MACRO_FILENAME


def test_manuscript_body_contains_no_hand_typed_results() -> None:
    assert verify_manuscript_values(TEX_PATH) == []


def test_every_macro_the_manuscript_uses_is_generated() -> None:
    assert undefined_macros(TEX_PATH, MACRO_PATH) == []


def test_the_check_is_not_passing_vacuously(tmp_path: Path) -> None:
    """A literal in the body must be caught, or the check proves nothing."""
    injected = TEX_PATH.read_text(encoding="utf-8").replace(
        r"\begin{abstract}",
        "\\begin{abstract}\nThe bias is 10.90 percentage points.\n",
        1,
    )
    candidate = tmp_path / "injected.tex"
    candidate.write_text(injected, encoding="utf-8")
    assert "10.90" in verify_manuscript_values(candidate)


def test_prose_years_are_not_mistaken_for_results(tmp_path: Path) -> None:
    candidate = tmp_path / "years.tex"
    candidate.write_text(
        "\\begin{document}\nThe 2022--2023 tightening.\n\\end{document}",
        encoding="utf-8",
    )
    assert verify_manuscript_values(candidate) == []


def test_a_missing_macro_is_reported(tmp_path: Path) -> None:
    candidate = tmp_path / "missing.tex"
    candidate.write_text(
        "\\begin{document}\nBias of \\BiasTotalHSeven pp.\n\\end{document}",
        encoding="utf-8",
    )
    assert undefined_macros(candidate, MACRO_PATH) == ["BiasTotalHSeven"]


def test_absent_manuscript_raises(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        verify_manuscript_values(tmp_path / "nothing.tex")


def test_generated_macros_are_committed_alongside_the_manuscript() -> None:
    """The paper must build from a clone without rerunning the pipeline."""
    assert MACRO_PATH.is_file()
    assert MACRO_PATH.read_text(encoding="utf-8").count("newcommand") >= 40


def test_repricing_title_contains_no_colon() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    title = source.split("\\title{")[1].split("\n")[0]
    assert ":" not in title


def test_repricing_paper_uses_generated_tables_and_figures() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    assert source.count(r"\input{tables/") >= 5
    assert source.count(r"\includegraphics") >= 3

    for relative in (
        "tables/portfolio_inputs.tex",
        "tables/estimation_coefficients.tex",
        "tables/kernel_bias.tex",
        "tables/half_life.tex",
        "tables/backtest_summary.tex",
        "figures/retail_stock_and_spread.pdf",
        "figures/kernel_comparison.pdf",
        "figures/pass_through_growth_paths.pdf",
    ):
        assert (PAPER_DIR / relative).is_file(), f"missing generated artefact: {relative}"


def test_repricing_paper_has_a_substantive_bibliography() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    assert source.count(r"\bibitem{") >= 10
