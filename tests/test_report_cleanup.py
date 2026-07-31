"""Guards for the report cleanup.

These read the report source and the generated tables. They exist because the
cleanup items were previously applied to a draft and then lost; a test is the
only thing that keeps them applied.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER = REPO_ROOT / "paper" / "portugal_public_debt_interest_report.tex"
TABLES = REPO_ROOT / "reports" / "tables"
CONFIG = REPO_ROOT / "config" / "default.yaml"


def _paper() -> str:
    if not PAPER.is_file():
        pytest.skip("paper source is not present")
    return PAPER.read_text(encoding="utf-8")


def _table(name: str) -> str:
    path = TABLES / name
    if not path.is_file():
        pytest.skip(f"{name} has not been generated")
    return path.read_text(encoding="utf-8")


def _title(source: str) -> str:
    return source.split("\\title{")[1].split("\n")[0]


def test_no_contradictory_ameco_text() -> None:
    source = _paper()
    # The extension carries no rows in this build, so nothing may claim it is
    # used, retained, or a limitation of the paper.
    assert "AMECO is used" not in source
    assert "linked pre-1995 extension" not in source
    assert "pre-1995 AMECO extension is not accounting-equivalent" not in source


def test_abstract_excludes_expenditure_and_revenue_totals() -> None:
    source = _paper()
    abstract = source.split("\\begin{abstract}")[1].split("\\end{abstract}")[0]
    assert "Total general-government expenditure" not in abstract
    assert r"\LatestGovernmentExpenditureEurBn" not in abstract
    assert r"\LatestGovernmentRevenueEurBn" not in abstract


def test_report_has_four_research_questions() -> None:
    source = _paper()
    assert "four research questions" in source
    assert "seven research questions" not in source

    start = source.index("four research questions")
    block = source[start : source.index("\\end{enumerate}", start)]
    assert block.count("\\item") == 4


def test_dependent_variable_phrase_absent() -> None:
    source = _paper().lower()
    assert "dependent variable" not in source
    assert "empirical strategy" not in source
    assert "main empirical sample" not in source


def test_summary_table_contains_n() -> None:
    content = _table("summary_statistics.tex")
    header = content.split("\\toprule")[1].split("\\\\")[0]
    assert " N " in header, "the summary table has no N column"


def test_tied_minimum_years_reported() -> None:
    """The minimum interest burden is reached twice; both years must appear."""
    content = _table("summary_statistics.tex")
    interest_row = next(
        line for line in content.splitlines() if line.startswith("Interest/GDP")
    )
    assert "2022, 2025" in interest_row, (
        f"tied minimum years are not both reported: {interest_row}"
    )


def test_title_contains_no_colon() -> None:
    assert ":" not in _title(_paper())


def test_no_near_empty_reproducibility_page() -> None:
    source = _paper()
    assert "Appendix E: Reproducibility Commands" not in source
    assert "\\begin{verbatim}" not in source


def test_plot_titles_not_duplicated() -> None:
    """Captions carry the title, so the figures must not repeat it."""
    plotting = (REPO_ROOT / "src" / "pt_debt_interest" / "plotting.py").read_text(
        encoding="utf-8"
    )
    for line in plotting.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("ax.set_title("), (
            f"figure sets its own title: {stripped}"
        )
        assert not stripped.startswith("ax_left.set_title(")


def test_variable_dictionary_layout() -> None:
    source = _paper()
    assert "\\begin{longtable}" in source, "the dictionary is not a longtable"
    # Identifiers must not hyphenate across lines or pages.
    assert "\\hyphenpenalty=10000" in source
    assert "\\exhyphenpenalty=10000" in source


def test_regime_label_is_neutral() -> None:
    """The 2015-2019 label must not imply ECB intervention began in 2015."""
    source = _paper()
    assert "ECB intervention and refinancing" not in source
    config = CONFIG.read_text(encoding="utf-8")
    assert "ECB intervention and refinancing" not in config
    assert "Low-rate and asset-purchase period" in config


def test_expenditure_and_revenue_replaced_by_one_table() -> None:
    source = _paper()
    assert "11_government_expenditure" not in source
    assert "12_government_revenue" not in source
    assert "interest_share_of_budget" in source

    content = _table("interest_share_of_budget.tex")
    assert "Interest (\\% of expenditure)" in content
    assert "Interest (\\% of revenue)" in content
