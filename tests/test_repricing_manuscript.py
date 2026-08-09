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
REPORT_DIR = Path("reports/repricing")


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
    assert source.count(r"\input{tables/") >= 7
    assert source.count(r"\includegraphics") >= 5

    for relative in (
        "tables/portfolio_inputs.tex",
        "tables/estimation_coefficients.tex",
        "tables/kernel_bias.tex",
        "tables/refixing_comparison.tex",
        "tables/half_life.tex",
        "tables/backtest_summary.tex",
        "tables/sensitivity_checks.tex",
        "tables/model_comparison.tex",
        "figures/retail_stock_and_spread.pdf",
        "figures/kernel_comparison.pdf",
        "figures/kernel_bootstrap_band.pdf",
        "figures/pass_through_growth_paths.pdf",
        "figures/scenario_fan_chart.pdf",
    ):
        assert (PAPER_DIR / relative).is_file(), f"missing generated artefact: {relative}"


def test_repricing_paper_has_a_substantive_bibliography() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    assert source.count(r"\bibitem{") >= 10


def test_repricing_paper_does_not_headline_the_old_point_estimate() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    abstract = source.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0]
    conclusion = source.split(r"\section{Conclusion}", 1)[1]
    assert r"\BiasTotalHOne" not in abstract
    assert r"\BiasInterestMioHOne" not in abstract
    assert r"\BiasTotalHOne" not in conclusion
    assert "bounded sensitivity" in abstract


def test_repricing_paper_states_the_current_bias_sign_pattern() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    assert "positive at one year" in source
    assert "negative at the longer reported horizons" in source
    assert "positive at the reported horizons" not in source


def test_repricing_terms_do_not_revert_to_old_bias_language() -> None:
    combined = "\n".join(
        [
            TEX_PATH.read_text(encoding="utf-8"),
            (PAPER_DIR / "tables" / "kernel_bias.tex").read_text(encoding="utf-8"),
            (PAPER_DIR / "tables" / "backtest_summary.tex").read_text(
                encoding="utf-8"
            ),
        ]
    )
    for stale in (
        "Scenario bias",
        "scenario bias",
        "central bias",
        "one-year bias",
        "Estimated share",
        "Total bias (pp)",
        "Out-of-sample backtest errors",
        "estimated repricing kernel",
        "not precise enough",
        "similarly weak",
        "observable lower-bound",
        "one-sided bound",
    ):
        assert stale not in combined

    assert "Scenario-minus-WAM repricing differences" in combined
    assert "Scenario exposure" in combined
    assert "Conditional historical validation errors" in combined
    assert "statistically precise" in TEX_PATH.read_text(encoding="utf-8")
    assert "precision is not identification" in TEX_PATH.read_text(encoding="utf-8")


def test_repricing_paper_includes_the_official_refixing_benchmark() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    normalised = " ".join(source.split())
    table = (PAPER_DIR / "tables" / "refixing_comparison.tex").read_text(
        encoding="utf-8"
    )
    assert r"\input{tables/refixing_comparison.tex}" in source
    assert "Official ESDM refixing benchmark" in table
    assert "WAM share" in table
    assert "Scenario minus ESDM" in table
    assert "monthly panel state at or before that date" in table
    assert "portfolio-basis conventions" in table
    assert "25.2" in table
    assert "50.9" in table
    assert "closer to the official ESDM value in the one-year window" in normalised
    assert "WAM is closer in the five-year cumulative window" in normalised
    assert "none has been performed" not in source
    assert "not against the debt manager's own refixing view" not in source


def test_backtest_prose_matches_current_winner_pattern() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    table = (PAPER_DIR / "tables" / "backtest_summary.tex").read_text(
        encoding="utf-8"
    )
    assert "2014 & Scenario kernel" in table
    assert "2018 & Scenario kernel" in table
    assert "2021 & WAM benchmark" in table
    assert "two of the three cut" in source
    assert "out of sample" not in source
    assert "out-of-sample" not in source
    assert "under a basis point at 2014 and 2018" not in source
    assert r"\BacktestMarginFourteen" in source
    assert r"\BacktestMarginEighteen" in source
    assert r"\BacktestMarginTwentyOne" in source
    assert "lower mean absolute error at all three cut dates" not in source


def test_repricing_paper_matches_revision7_sensitivity_and_limitations() -> None:
    source = TEX_PATH.read_text(encoding="utf-8")
    normalised = " ".join(source.split())
    assert "the sign is robust to the reported reset-timing alternatives" in normalised
    assert "reset assumption reverses the sign" not in source
    assert "two-year reset assumption reverses" not in source
    assert "mutually exclusive instrument categories" not in source
    assert "four-way split" in source
    assert "new retail funding" in source
    assert "not a repricing event for the opening stock" in normalised


def test_current_repricing_reports_do_not_repeat_superseded_claims() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(REPORT_DIR.glob("*.md"))
    )
    for stale in (
        "10.90",
        "10.9",
        "EUR 300 million",
        "about 300 million",
        "positive at every horizon",
        "The sign is stable",
        "burden paper's flaw",
        "material correction to the earlier paper",
        "observable lower-bound",
        "Scenario bias",
        "scenario bias",
        "central bias",
        "bias result",
        "Estimated share",
    ):
        assert stale not in combined
