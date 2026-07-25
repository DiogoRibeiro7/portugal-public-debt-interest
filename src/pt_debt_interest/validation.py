"""Data-quality, reconciliation, and accounting-identity checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

PROVENANCE_COLUMNS = [
    "source",
    "source_vintage",
    "accounting_basis",
    "observation_status",
    "retrieval_timestamp_utc",
    "source_flags",
    "basis_break",
]


@dataclass(frozen=True)
class CheckResult:
    """One validation result."""

    name: str
    passed: bool
    severity: str
    detail: str
    affected_years: list[int]


def validate_dataset(
    frame: pd.DataFrame,
    expected_start_year: int,
    expected_end_year: int,
    ratio_tolerance_pp: float,
    identity_tolerance_pp: float,
) -> dict[str, Any]:
    """Run mandatory and diagnostic validations."""
    checks: list[CheckResult] = []

    duplicated = frame.loc[frame["year"].duplicated(), "year"].astype(int).tolist()
    checks.append(
        CheckResult(
            name="unique_years",
            passed=not duplicated,
            severity="error",
            detail="Each analytical year must occur once.",
            affected_years=duplicated,
        )
    )

    missing_provenance = [
        column for column in PROVENANCE_COLUMNS if column not in frame.columns
    ]
    checks.append(
        CheckResult(
            name="provenance_columns_present",
            passed=not missing_provenance,
            severity="warning",
            detail=f"Missing provenance columns: {missing_provenance}",
            affected_years=[],
        )
    )

    expected = set(range(expected_start_year, expected_end_year + 1))
    actual = set(frame.loc[frame["accounting_basis"] == "ESA2010", "year"].astype(int))
    missing_years = sorted(expected.difference(actual))
    checks.append(
        CheckResult(
            name="main_series_year_coverage",
            passed=not missing_years,
            severity="warning",
            detail="Missing years in the harmonised ESA 2010 main series.",
            affected_years=missing_years,
        )
    )

    if {"interest_pct_gdp_official", "interest_pct_gdp_calculated"}.issubset(frame.columns):
        difference = (
            frame["interest_pct_gdp_official"] - frame["interest_pct_gdp_calculated"]
        ).abs()
        affected = frame.loc[difference > ratio_tolerance_pp, "year"].astype(int).tolist()
        checks.append(
            CheckResult(
                name="interest_ratio_reconciliation",
                passed=not affected,
                severity="warning",
                detail=(
                    "Official and calculated interest ratios differ by more than "
                    f"{ratio_tolerance_pp} pp."
                ),
                affected_years=affected,
            )
        )

    if {"debt_pct_gdp_official", "debt_pct_gdp_calculated"}.issubset(frame.columns):
        difference = (frame["debt_pct_gdp_official"] - frame["debt_pct_gdp_calculated"]).abs()
        affected = frame.loc[difference > ratio_tolerance_pp, "year"].astype(int).tolist()
        checks.append(
            CheckResult(
                name="debt_ratio_reconciliation",
                passed=not affected,
                severity="warning",
                detail=(
                    "Official and calculated debt ratios differ by more than "
                    f"{ratio_tolerance_pp} pp."
                ),
                affected_years=affected,
            )
        )

    if {
        "primary_balance_pct_gdp",
        "overall_balance_pct_gdp",
        "interest_pct_gdp",
    }.issubset(frame.columns):
        identity_error = (
            frame["primary_balance_pct_gdp"]
            - frame["overall_balance_pct_gdp"]
            - frame["interest_pct_gdp"]
        ).abs()
        affected = frame.loc[identity_error > identity_tolerance_pp, "year"].astype(int).tolist()
        checks.append(
            CheckResult(
                name="primary_balance_identity",
                passed=not affected,
                severity="error",
                detail="Primary balance must equal overall balance plus interest expenditure.",
                affected_years=affected,
            )
        )

    observed_forecast_overlap: list[int] = []
    if {"year", "observation_status", "source"}.issubset(frame.columns):
        for year, group in frame.groupby("year"):
            statuses = set(group["observation_status"].dropna().astype(str))
            if {"observed", "forecast"}.issubset(statuses):
                observed_forecast_overlap.append(int(str(year)))
    checks.append(
        CheckResult(
            name="observed_forecast_separation",
            passed=not observed_forecast_overlap,
            severity="error",
            detail=(
                "A year must not be represented simultaneously as observed and "
                "forecast after harmonisation."
            ),
            affected_years=observed_forecast_overlap,
        )
    )

    missing_basis_break: list[int] = []
    if {"year", "basis_break"}.issubset(frame.columns):
        boundary_rows = frame.loc[frame["year"].astype(int).eq(expected_start_year)]
        if boundary_rows.empty or not boundary_rows["basis_break"].fillna(False).astype(bool).any():
            missing_basis_break = [expected_start_year]
    checks.append(
        CheckResult(
            name="basis_boundary_marked",
            passed=not missing_basis_break,
            severity="warning",
            detail="The main-series accounting-basis boundary should be marked.",
            affected_years=missing_basis_break,
        )
    )

    payload = [asdict(check) for check in checks]
    return {
        "passed": all(check.passed for check in checks if check.severity == "error"),
        "checks": payload,
    }
