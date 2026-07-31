"""Guards that validation discrepancies and data revisions are stated, not summarised.

The failure these protect against is a report that says "one warning remains"
without saying which years, by how much, or against what tolerance — and a
revision log that invents a cause it cannot know.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.revisions import (
    REVISION_REASONS,
    build_revision_log,
    build_validation_detail,
    classify_revision,
    error_level_failures,
    revision_log_markdown,
    validation_detail_markdown,
    write_validation_and_revision_reports,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER = REPO_ROOT / "paper" / "portugal_public_debt_interest_report.tex"
PROCESSED = REPO_ROOT / "data" / "processed" / "portugal_debt_interest.csv"
TOLERANCE = 0.15


def _frame() -> pd.DataFrame:
    if not PROCESSED.is_file():
        pytest.skip("processed dataset has not been generated")
    return pd.read_csv(PROCESSED)


def _paper() -> str:
    if not PAPER.is_file():
        pytest.skip("paper source is not present")
    return PAPER.read_text(encoding="utf-8")


def _vintage(debt_ratio: float, checksum: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [1997, 1998],
            "debt_pct_gdp": [debt_ratio, 55.6],
            "interest_pct_gdp": [3.8, 3.1],
            "debt_pct_gdp_source_sha256": [checksum, checksum],
        }
    )


def test_validation_warning_contains_actual_values() -> None:
    detail = build_validation_detail(_frame(), TOLERANCE)
    breaches = detail.loc[detail["exceeds_tolerance"]]
    assert set(breaches["year"]) == {1997, 1998}

    row_1997 = detail.loc[detail["year"].eq(1997)].iloc[0]
    assert row_1997["official_pct_gdp"] == pytest.approx(58.7)
    assert row_1997["reconstructed_pct_gdp"] == pytest.approx(57.684795, abs=1e-5)
    assert row_1997["absolute_difference_pp"] == pytest.approx(1.015205, abs=1e-5)

    row_1998 = detail.loc[detail["year"].eq(1998)].iloc[0]
    assert row_1998["absolute_difference_pp"] == pytest.approx(-0.352231, abs=1e-5)

    markdown = validation_detail_markdown(detail, (1997, 1998))
    assert "58.70" in markdown and "57.684795" in markdown
    assert "55.60" in markdown and "55.952231" in markdown

    # The report must carry the values, not a summary sentence.
    paper = _paper()
    assert "One warning" not in paper
    assert r"\DebtRatioOfficialNineteenNinetySeven" in paper
    assert r"\DebtRatioDifferenceNineteenNinetyEightPp" in paper


def test_tolerance_is_reported() -> None:
    detail = build_validation_detail(_frame(), TOLERANCE)
    assert (detail["tolerance_pp"] == TOLERANCE).all()
    assert str(TOLERANCE) in validation_detail_markdown(detail, (1997, 1998))
    assert r"\ValidationTolerancePp" in _paper()


def test_unknown_reason_not_replaced_with_speculation() -> None:
    detail = build_validation_detail(_frame(), TOLERANCE)
    breaches = detail.loc[detail["exceeds_tolerance"]]
    assert (breaches["explanation_classification"] == "Unknown").all()

    # No mechanism may invent a cause outside the permitted classifications.
    assert classify_revision("unknown", "abc") == "unknown"
    assert classify_revision("abc", "abc") == "unknown"
    log = build_revision_log(_vintage(58.7, "abc"), _vintage(57.0, "def"))
    assert set(log["reason_classification"]).issubset(set(REVISION_REASONS))

    # The report must not assert a cause for the breach. Scope the check to
    # the validation passage: "because" is ordinary prose elsewhere.
    paper = _paper()
    start = paper.index("The empirical series passed every error-severity")
    passage = paper[start : paper.index("\section", start)].lower()
    assert "nothing in the data identifies which side moved" in passage
    assert r"\debtratiocausenineteenninetyseven" in passage
    for speculation in ("caused by", "is explained by", "results from a revision"):
        assert speculation not in passage


def test_checksum_change_detected() -> None:
    current = _vintage(58.7, "checksum-new")
    previous = _vintage(57.0, "checksum-old")
    log = build_revision_log(current, previous)

    changed = log.loc[log["variable"].eq("debt_pct_gdp") & log["year"].eq(1997)]
    assert not changed.empty
    row = changed.iloc[0]
    assert row["previous_checksum"] == "checksum-old"
    assert row["current_checksum"] == "checksum-new"
    assert row["reason_classification"] == "source revision"

    # An unchanged checksum is not evidence of a source revision.
    same = build_revision_log(_vintage(58.7, "same"), _vintage(57.0, "same"))
    assert same.iloc[0]["reason_classification"] == "unknown"


def test_previous_vintage_difference_logged() -> None:
    current = _vintage(58.7, "new")
    previous = _vintage(57.0, "old")
    log = build_revision_log(current, previous)

    row = log.loc[log["year"].eq(1997) & log["variable"].eq("debt_pct_gdp")].iloc[0]
    assert row["previous_value"] == pytest.approx(57.0)
    assert row["current_value"] == pytest.approx(58.7)
    assert row["absolute_change"] == pytest.approx(1.7)
    assert row["relative_change_pct"] == pytest.approx(1.7 / 57.0 * 100.0)

    assert "Changed values" in revision_log_markdown(log, previous_available=True)
    # With nothing to compare against, the log says so rather than implying none.
    empty = build_revision_log(current, None)
    assert empty.empty
    text = revision_log_markdown(empty, previous_available=False)
    assert "No previous processed vintage was available" in text


def test_error_level_validation_stops_report_build() -> None:
    failing = {
        "passed": False,
        "checks": [
            {"name": "primary_balance_identity", "passed": False, "severity": "error"},
            {"name": "debt_ratio_reconciliation", "passed": False, "severity": "warning"},
        ],
    }
    assert error_level_failures(failing) == ["primary_balance_identity"]

    warning_only = {
        "passed": False,
        "checks": [
            {"name": "debt_ratio_reconciliation", "passed": False, "severity": "warning"}
        ],
    }
    assert error_level_failures(warning_only) == []

    # The CLI must consult it before building the report.
    cli = (REPO_ROOT / "src" / "pt_debt_interest" / "cli.py").read_text(encoding="utf-8")
    assert "error_level_failures" in cli
    assert "refusing to build the" in cli


def test_report_appendix_contains_validation_counts() -> None:
    paper = _paper()
    for macro in (
        r"\ValidationErrorCount",
        r"\ValidationWarningCount",
        r"\ValidationAllErrorsPassed",
        r"\MaxRatioDiscrepancyPp",
        r"\EarliestRetrievalTimestamp",
        r"\LatestRetrievalTimestamp",
        r"\AcceptedObservationStatuses",
    ):
        assert macro in paper, f"{macro} is not reported in the appendix"


def test_writer_produces_the_four_artefacts(tmp_path: Path) -> None:
    frame = _frame()
    processed = tmp_path / "processed"
    processed.mkdir()
    outputs = write_validation_and_revision_reports(
        frame, tmp_path / "reports", processed, TOLERANCE
    )
    assert set(outputs) == {
        "validation_detail_csv",
        "validation_detail_md",
        "revision_log_csv",
        "revision_log_md",
    }
    for path in outputs.values():
        assert path.is_file()

    # The vintage is archived, so a second run has something to compare against.
    second = write_validation_and_revision_reports(
        frame, tmp_path / "reports", processed, TOLERANCE
    )
    assert "No previous processed vintage" not in second["revision_log_md"].read_text(
        encoding="utf-8"
    )
