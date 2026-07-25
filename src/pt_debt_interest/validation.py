"""Data-quality, reconciliation, and accounting-identity checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


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
                detail=f"Official and calculated interest ratios differ by more than {ratio_tolerance_pp} pp.",
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
                detail=f"Official and calculated debt ratios differ by more than {ratio_tolerance_pp} pp.",
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
        grouped = frame.groupby("year")["observation_status"].agg(lambda x: set(x.dropna()))
        observed_forecast_overlap = [
            int(year) for year, statuses in grouped.items() if {"observed", "forecast"}.issubset(statuses)
        ]
    checks.append(
        CheckResult(
            name="observed_forecast_separation",
            passed=not observed_forecast_overlap,
            severity="error",
            detail="A year must not be represented simultaneously as observed and forecast after harmonisation.",
            affected_years=observed_forecast_overlap,
        )
    )

    payload = [asdict(check) for check in checks]
    return {
        "passed": all(check.passed for check in checks if check.severity == "error"),
        "checks": payload,
    }
