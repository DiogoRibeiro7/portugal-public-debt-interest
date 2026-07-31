"""Validation detail and data-revision auditing.

Two things live here. The first turns "one warning remains" into the actual
years, values, differences, and tolerance. The second compares the current
processed vintage with the previously archived one and records every changed
value with both checksums.

Neither speculates. Where the cause of a discrepancy or a revision is not
determinable from the data, it is classified ``Unknown``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from .exceptions import ValidationError

#: Where the previous processed vintage is archived for the next comparison.
VINTAGE_ARCHIVE: Final[str] = ".vintage"
PREVIOUS_VINTAGE_FILENAME: Final[str] = "previous_portugal_debt_interest.csv"

#: Reason classifications permitted in the revision log. No other value may be
#: written, and nothing may be inferred beyond what the data supports.
REVISION_REASONS: Final[tuple[str, ...]] = (
    "source revision",
    "parser change",
    "dimension-filter change",
    "unit conversion change",
    "unknown",
)

RATIO_PAIRS: Final[dict[str, tuple[str, str]]] = {
    "debt_pct_gdp": ("debt_pct_gdp_official", "debt_pct_gdp_calculated"),
    "interest_pct_gdp": ("interest_pct_gdp_official", "interest_pct_gdp_calculated"),
}


def build_validation_detail(
    frame: pd.DataFrame,
    tolerance_pp: float,
    ratio: str = "debt_pct_gdp",
) -> pd.DataFrame:
    """Build the per-year reconciliation detail for a published ratio."""
    if ratio not in RATIO_PAIRS:
        raise ValidationError(f"no reconciliation defined for {ratio}")
    official_column, calculated_column = RATIO_PAIRS[ratio]
    missing = {official_column, calculated_column}.difference(frame.columns)
    if missing:
        raise ValidationError(f"validation detail is missing columns: {sorted(missing)}")

    working = frame.sort_values("year").copy()
    official = pd.to_numeric(working[official_column], errors="coerce")
    calculated = pd.to_numeric(working[calculated_column], errors="coerce")
    difference = official - calculated

    relative = pd.Series(np.nan, index=working.index, dtype=float)
    usable = calculated.abs() > 0
    relative.loc[usable] = difference.loc[usable] / calculated.loc[usable] * 100.0

    detail = pd.DataFrame(
        {
            "year": pd.to_numeric(working["year"], errors="coerce").astype("Int64"),
            "ratio": ratio,
            "official_pct_gdp": official,
            "reconstructed_pct_gdp": calculated,
            "absolute_difference_pp": difference,
            "relative_difference_pct": relative,
            "tolerance_pp": tolerance_pp,
        }
    )
    detail["exceeds_tolerance"] = detail["absolute_difference_pp"].abs() > tolerance_pp
    detail["warning_level"] = np.where(
        detail["absolute_difference_pp"].isna(),
        "not evaluated",
        np.where(detail["exceeds_tolerance"], "warning", "within tolerance"),
    )
    for column, source in (
        ("source_vintage", "source_vintage"),
        ("source_checksum_sha256", "source_checksum_sha256"),
    ):
        detail[column] = (
            working[source].astype(str).to_numpy()
            if source in working.columns
            else "unknown"
        )

    # The published ratio and the reconstruction come from different Eurostat
    # datasets. Nothing in the data identifies which side moved, so the cause is
    # not asserted.
    detail["explanation_classification"] = np.where(
        detail["exceeds_tolerance"], "Unknown", "not applicable"
    )
    return detail.reset_index(drop=True)


def validation_detail_markdown(detail: pd.DataFrame, focus_years: tuple[int, ...]) -> str:
    """Render the reconciliation detail, naming the breaching years explicitly."""
    breaches = detail.loc[detail["exceeds_tolerance"]]
    tolerance = float(detail["tolerance_pp"].dropna().iloc[0]) if len(detail) else 0.0

    lines = [
        "# Validation detail",
        "",
        f"Configured tolerance: {tolerance} percentage points.",
        f"Years evaluated: {int(detail['year'].notna().sum())}.",
        f"Years exceeding tolerance: {len(breaches)}.",
        "",
    ]
    if breaches.empty:
        lines.append("No year exceeds the configured tolerance.")
    else:
        lines.append("## Years exceeding tolerance")
        lines.append("")
        lines.append(
            "| Year | Official | Reconstructed | Difference (pp) | "
            "Relative (%) | Tolerance (pp) | Level | Cause |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for row in breaches.itertuples():
            lines.append(
                f"| {int(float(str(row.year)))} | {row.official_pct_gdp:.2f} | "
                f"{row.reconstructed_pct_gdp:.6f} | "
                f"{row.absolute_difference_pp:+.4f} | "
                f"{row.relative_difference_pct:+.4f} | {row.tolerance_pp} | "
                f"{row.warning_level} | {row.explanation_classification} |"
            )

    focus = detail.loc[detail["year"].isin(list(focus_years))]
    if not focus.empty:
        lines.extend(["", "## Focus years", ""])
        for row in focus.itertuples():
            lines.append(
                f"- {int(float(str(row.year)))}: official {row.official_pct_gdp:.2f}, "
                f"reconstructed {row.reconstructed_pct_gdp:.6f}, "
                f"difference {row.absolute_difference_pp:+.4f} pp against a "
                f"tolerance of {row.tolerance_pp} pp "
                f"({row.warning_level}; cause: {row.explanation_classification})."
            )
    lines.append("")
    return "\n".join(lines)


def _checksum_for(frame: pd.DataFrame, year: int, variable: str) -> str:
    column = f"{variable}_source_sha256"
    if column not in frame.columns:
        column = "source_checksum_sha256"
    if column not in frame.columns:
        return "unknown"
    rows = frame.loc[frame["year"].eq(year), column]
    if rows.empty or pd.isna(rows.iloc[0]):
        return "unknown"
    return str(rows.iloc[0])


def classify_revision(
    previous_checksum: str,
    current_checksum: str,
) -> str:
    """Classify a changed value using only what the data supports.

    A changed source checksum is evidence of a source revision. Anything else
    is not determinable from the processed dataset alone and is reported as
    unknown rather than guessed.
    """
    if previous_checksum == "unknown" or current_checksum == "unknown":
        return "unknown"
    return "source revision" if previous_checksum != current_checksum else "unknown"


def build_revision_log(
    current: pd.DataFrame,
    previous: pd.DataFrame | None,
    variables: tuple[str, ...] = (
        "interest_mio_eur",
        "interest_pct_gdp",
        "debt_pct_gdp",
        "nominal_gdp_mio_eur",
        "average_debt_interest_rate_pct",
    ),
    country: str = "PT",
) -> pd.DataFrame:
    """Compare two processed vintages value by value."""
    columns = [
        "country",
        "year",
        "variable",
        "previous_value",
        "current_value",
        "absolute_change",
        "relative_change_pct",
        "previous_checksum",
        "current_checksum",
        "reason_classification",
    ]
    if previous is None or previous.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    previous_indexed = previous.set_index("year")
    for variable in variables:
        if variable not in current.columns or variable not in previous.columns:
            continue
        for row in current.itertuples():
            year = int(float(str(row.year)))
            if year not in previous_indexed.index:
                continue
            current_value = pd.to_numeric(getattr(row, variable), errors="coerce")
            previous_value = pd.to_numeric(
                previous_indexed.loc[year, variable], errors="coerce"
            )
            both_missing = bool(pd.isna(current_value)) and bool(pd.isna(previous_value))
            if both_missing:
                continue
            unchanged = (
                bool(pd.notna(current_value))
                and bool(pd.notna(previous_value))
                and float(current_value) == float(previous_value)
            )
            if unchanged:
                continue
            previous_checksum = _checksum_for(previous, year, variable)
            current_checksum = _checksum_for(current, year, variable)
            absolute = (
                float(current_value) - float(previous_value)
                if pd.notna(current_value) and pd.notna(previous_value)
                else np.nan
            )
            relative = (
                absolute / float(previous_value) * 100.0
                if pd.notna(absolute) and previous_value not in (0, np.nan)
                else np.nan
            )
            rows.append(
                {
                    "country": country,
                    "year": year,
                    "variable": variable,
                    "previous_value": previous_value,
                    "current_value": current_value,
                    "absolute_change": absolute,
                    "relative_change_pct": relative,
                    "previous_checksum": previous_checksum,
                    "current_checksum": current_checksum,
                    "reason_classification": classify_revision(
                        previous_checksum, current_checksum
                    ),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def revision_log_markdown(log: pd.DataFrame, previous_available: bool) -> str:
    """Render the revision log, stating plainly when there is nothing to compare."""
    lines = ["# Data revision log", ""]
    if not previous_available:
        lines.extend(
            [
                "No previous processed vintage was available for comparison.",
                "",
                "The processed directory is not version controlled, so the first "
                "build has nothing to diff against. This build has been archived; "
                "the next build will compare against it.",
                "",
            ]
        )
        return "\n".join(lines)
    if log.empty:
        lines.extend(["No value changed against the previous vintage.", ""])
        return "\n".join(lines)

    lines.extend([f"Changed values: {len(log)}.", ""])
    lines.append(
        "| Country | Year | Variable | Previous | Current | Change | "
        "Relative (%) | Reason |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in log.itertuples():
        lines.append(
            f"| {row.country} | {row.year} | {row.variable} | "
            f"{row.previous_value} | {row.current_value} | "
            f"{row.absolute_change} | {row.relative_change_pct} | "
            f"{row.reason_classification} |"
        )
    lines.append("")
    return "\n".join(lines)


def load_previous_vintage(processed_dir: Path) -> pd.DataFrame | None:
    """Read the archived previous processed vintage, if one exists."""
    path = processed_dir / VINTAGE_ARCHIVE / PREVIOUS_VINTAGE_FILENAME
    if not path.is_file():
        return None
    return pd.read_csv(path)


def archive_vintage(frame: pd.DataFrame, processed_dir: Path) -> Path:
    """Archive the current processed vintage for the next comparison."""
    archive_dir = processed_dir / VINTAGE_ARCHIVE
    archive_dir.mkdir(parents=True, exist_ok=True)
    path = archive_dir / PREVIOUS_VINTAGE_FILENAME
    frame.to_csv(path, index=False)
    return path


def error_level_failures(validation_result: dict[str, object]) -> list[str]:
    """Names of error-severity checks that failed."""
    checks = validation_result.get("checks", [])
    if not isinstance(checks, list):
        return []
    return [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict)
        and not check.get("passed", True)
        and str(check.get("severity")) == "error"
    ]


def write_validation_and_revision_reports(
    frame: pd.DataFrame,
    reports_dir: Path,
    processed_dir: Path,
    tolerance_pp: float,
    focus_years: tuple[int, ...] = (1997, 1998),
) -> dict[str, Path]:
    """Write the four audit artefacts and archive the current vintage."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    detail = build_validation_detail(frame, tolerance_pp)
    previous = load_previous_vintage(processed_dir)
    log = build_revision_log(frame, previous)

    outputs = {
        "validation_detail_csv": reports_dir / "validation_detail.csv",
        "validation_detail_md": reports_dir / "validation_detail.md",
        "revision_log_csv": reports_dir / "data_revision_log.csv",
        "revision_log_md": reports_dir / "data_revision_log.md",
    }
    detail.to_csv(outputs["validation_detail_csv"], index=False)
    outputs["validation_detail_md"].write_text(
        validation_detail_markdown(detail, focus_years), encoding="utf-8"
    )
    log.to_csv(outputs["revision_log_csv"], index=False)
    outputs["revision_log_md"].write_text(
        revision_log_markdown(log, previous is not None), encoding="utf-8"
    )
    archive_vintage(frame, processed_dir)
    return outputs
