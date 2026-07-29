"""Fiscal metrics and accounting transformations."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_BASE_COLUMNS = {
    "year",
    "interest_mio_eur",
    "nominal_gdp_mio_eur",
    "debt_mio_eur",
}


def compute_average_debt_interest_rate(
    interest_nominal: pd.Series,
    previous_debt_nominal: pd.Series,
    current_debt_nominal: pd.Series,
) -> pd.Series:
    """Return the average-debt descriptive rate as a decimal ratio."""
    denominator = (previous_debt_nominal + current_debt_nominal) / 2.0
    invalid = denominator.le(0) | ~np.isfinite(denominator)
    rate = interest_nominal / denominator
    return rate.mask(invalid)


def compute_debt_dynamics_interest_rate(
    interest_nominal: pd.Series,
    previous_debt_nominal: pd.Series,
) -> pd.Series:
    """Return the debt-dynamics rate as a decimal ratio."""
    invalid = previous_debt_nominal.le(0) | ~np.isfinite(previous_debt_nominal)
    rate = interest_nominal / previous_debt_nominal
    return rate.mask(invalid)


def assign_regime(year: int, boundaries: list[dict[str, object]]) -> str | None:
    """Return the configured regime label for a year."""
    for boundary in boundaries:
        start = _regime_boundary_year(boundary["start"], "start")
        end = _regime_boundary_year(boundary["end"], "end")
        if start <= year <= end:
            return str(boundary["label"])
    return None


def _regime_boundary_year(value: object, label: str) -> int:
    """Parse a regime boundary year without truncating malformed values."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"regime boundary {label} year must be numeric")
    try:
        numeric = float(value)
    except ValueError as exc:
        raise ValueError(f"regime boundary {label} year must be numeric") from exc
    if not np.isfinite(numeric) or numeric % 1 != 0:
        raise ValueError(f"regime boundary {label} year must be a whole number")
    return int(numeric)


def _validate_percentage_scale(frame: pd.DataFrame) -> None:
    """Detect likely decimal-ratio inputs in persisted percentage columns."""
    if "debt_pct_gdp_official" not in frame.columns:
        return
    debt_ratio = pd.to_numeric(frame["debt_pct_gdp_official"], errors="coerce").dropna()
    if not debt_ratio.empty and debt_ratio.abs().median() <= 2.0:
        raise ValueError("debt_pct_gdp_official must be expressed as a percentage, not a ratio")


def _validate_optional_percentages(frame: pd.DataFrame) -> None:
    """Reject malformed optional percentage inputs before derived calculations."""
    for column in [
        "interest_pct_gdp_official",
        "debt_pct_gdp_official",
        "overall_balance_pct_gdp",
        "government_expenditure_pct_gdp_official",
        "government_revenue_pct_gdp_official",
    ]:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid = (frame[column].notna() & values.isna()) | (
            values.notna() & ~np.isfinite(values)
        )
        affected_years = frame.loc[invalid, "year"].astype(int).tolist()
        if affected_years:
            raise ValueError(f"{column} must be numeric and finite for years: {affected_years}")


def _validate_annual_input(frame: pd.DataFrame) -> None:
    """Reject inputs that make lagged annual calculations ambiguous."""
    if frame["year"].isna().any():
        raise ValueError("annual metrics require non-missing years")
    try:
        numeric_years = pd.to_numeric(frame["year"], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("annual metrics require numeric years") from exc
    if ((~np.isfinite(numeric_years)) | numeric_years.mod(1).ne(0)).any():
        raise ValueError("annual metrics require whole-number years")
    years = numeric_years.astype(int)
    duplicate_years = years.loc[years.duplicated(keep=False)].tolist()
    if duplicate_years:
        raise ValueError(f"annual metrics require unique years: {duplicate_years}")


def _validate_positive_denominators(frame: pd.DataFrame) -> None:
    """Reject non-positive values used as metric denominators."""
    for column in ["nominal_gdp_mio_eur", "debt_mio_eur"]:
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid = (frame[column].notna() & values.isna()) | (
            values.notna() & (~np.isfinite(values) | values.le(0))
        )
        affected_years = frame.loc[invalid, "year"].astype(int).tolist()
        if affected_years:
            raise ValueError(f"{column} must be finite and positive for years: {affected_years}")


def _validate_growth_factors(frame: pd.DataFrame) -> None:
    """Reject growth values that make factor-based calculations undefined."""
    if "real_gdp_growth_pct" not in frame.columns:
        return
    values = pd.to_numeric(frame["real_gdp_growth_pct"], errors="coerce")
    invalid = (frame["real_gdp_growth_pct"].notna() & values.isna()) | (
        values.notna() & (~np.isfinite(values) | values.le(-100))
    )
    affected_years = frame.loc[invalid, "year"].astype(int).tolist()
    if affected_years:
        raise ValueError(
            "real_gdp_growth_pct must be finite and greater than -100 "
            f"for years: {affected_years}"
        )


def _same_accounting_basis_as_previous(output: pd.DataFrame) -> pd.Series:
    """Return rows whose lagged calculations stay within one accounting basis."""
    if "accounting_basis" not in output.columns:
        return pd.Series(True, index=output.index)
    basis = output["accounting_basis"].astype("string")
    return basis.eq(basis.shift(1)).fillna(False)


def calculate_metrics(
    frame: pd.DataFrame,
    regime_boundaries: list[dict[str, object]] | None = None,
) -> pd.DataFrame:
    """Calculate the analytical annual indicators.

    Parameters
    ----------
    frame:
        Annual source data indexed by a `year` column.
    regime_boundaries:
        Optional list of dictionaries with `start`, `end`, and `label`.
    """
    missing = REQUIRED_BASE_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    _validate_annual_input(frame)
    _validate_optional_percentages(frame)
    _validate_percentage_scale(frame)
    _validate_positive_denominators(frame)
    _validate_growth_factors(frame)

    output = frame.sort_values("year").copy()
    output["interest_pct_gdp_calculated"] = (
        output["interest_mio_eur"] / output["nominal_gdp_mio_eur"] * 100.0
    )
    output["debt_pct_gdp_calculated"] = (
        output["debt_mio_eur"] / output["nominal_gdp_mio_eur"] * 100.0
    )
    if "government_expenditure_mio_eur" in output.columns:
        output["government_expenditure_pct_gdp_calculated"] = (
            output["government_expenditure_mio_eur"]
            / output["nominal_gdp_mio_eur"]
            * 100.0
        )
    if "government_revenue_mio_eur" in output.columns:
        output["government_revenue_pct_gdp_calculated"] = (
            output["government_revenue_mio_eur"] / output["nominal_gdp_mio_eur"] * 100.0
        )
    same_basis = _same_accounting_basis_as_previous(output)
    output["nominal_gdp_growth_pct"] = output["nominal_gdp_mio_eur"].pct_change() * 100.0
    output.loc[~same_basis, "nominal_gdp_growth_pct"] = np.nan

    previous_debt = output["debt_mio_eur"].shift(1)
    output["debt_dynamics_interest_rate"] = compute_debt_dynamics_interest_rate(
        output["interest_mio_eur"],
        previous_debt,
    )
    output["average_debt_interest_rate"] = compute_average_debt_interest_rate(
        output["interest_mio_eur"],
        previous_debt,
        output["debt_mio_eur"],
    )
    output.loc[~same_basis, "debt_dynamics_interest_rate"] = np.nan
    output.loc[~same_basis, "average_debt_interest_rate"] = np.nan
    output["debt_dynamics_interest_rate_pct"] = output["debt_dynamics_interest_rate"] * 100.0
    output["average_debt_interest_rate_pct"] = output["average_debt_interest_rate"] * 100.0

    if "real_gdp_growth_pct" in output.columns:
        nominal_factor = 1.0 + output["nominal_gdp_growth_pct"] / 100.0
        real_factor = 1.0 + output["real_gdp_growth_pct"] / 100.0
        output["gdp_deflator_growth_pct"] = (nominal_factor / real_factor - 1.0) * 100.0

    interest_ratio = output.get("interest_pct_gdp_official")
    if interest_ratio is None:
        interest_ratio = output["interest_pct_gdp_calculated"]
    else:
        interest_ratio = interest_ratio.fillna(output["interest_pct_gdp_calculated"])
    output["interest_pct_gdp"] = interest_ratio

    debt_ratio = output.get("debt_pct_gdp_official")
    if debt_ratio is None:
        debt_ratio = output["debt_pct_gdp_calculated"]
    else:
        debt_ratio = debt_ratio.fillna(output["debt_pct_gdp_calculated"])
    output["debt_pct_gdp"] = debt_ratio

    if "government_expenditure_mio_eur" in output.columns:
        spending_ratio = output.get("government_expenditure_pct_gdp_official")
        if spending_ratio is None:
            spending_ratio = output["government_expenditure_pct_gdp_calculated"]
        else:
            spending_ratio = spending_ratio.fillna(
                output["government_expenditure_pct_gdp_calculated"]
            )
        output["government_expenditure_pct_gdp"] = spending_ratio
    if "government_revenue_mio_eur" in output.columns:
        revenue_ratio = output.get("government_revenue_pct_gdp_official")
        if revenue_ratio is None:
            revenue_ratio = output["government_revenue_pct_gdp_calculated"]
        else:
            revenue_ratio = revenue_ratio.fillna(output["government_revenue_pct_gdp_calculated"])
        output["government_revenue_pct_gdp"] = revenue_ratio

    if "overall_balance_pct_gdp" in output.columns:
        output["primary_balance_pct_gdp"] = (
            output["overall_balance_pct_gdp"] + output["interest_pct_gdp"]
        )

    debt_ratio_lag = output["debt_pct_gdp"].shift(1) / 100.0
    debt_ratio = output["debt_pct_gdp"] / 100.0
    rate = output["debt_dynamics_interest_rate"]
    growth = output["nominal_gdp_growth_pct"] / 100.0
    growth_denominator = 1.0 + growth
    output["interest_growth_differential"] = rate - growth
    output["debt_stabilising_primary_balance_before_sfa"] = (
        ((rate - growth) / growth_denominator) * debt_ratio_lag
    )
    output["observed_debt_ratio_change"] = debt_ratio - debt_ratio_lag
    output["interest_growth_contribution"] = (
        ((rate - growth) / growth_denominator) * debt_ratio_lag
    )
    output["interest_growth_differential_pct"] = output["interest_growth_differential"] * 100.0
    output["debt_stabilising_primary_balance_before_sfa_pct_gdp"] = (
        output["debt_stabilising_primary_balance_before_sfa"] * 100.0
    )
    output["observed_debt_ratio_change_pp"] = output["observed_debt_ratio_change"] * 100.0
    output["interest_growth_contribution_pp"] = output["interest_growth_contribution"] * 100.0
    if "primary_balance_pct_gdp" in output.columns:
        output["primary_balance_contribution"] = -output["primary_balance_pct_gdp"] / 100.0
        output["stock_flow_adjustment"] = (
            output["observed_debt_ratio_change"]
            - output["interest_growth_contribution"]
            - output["primary_balance_contribution"]
        )
        output["reconstructed_debt_ratio_change"] = (
            output["interest_growth_contribution"]
            + output["primary_balance_contribution"]
            + output["stock_flow_adjustment"]
        )
        output["debt_dynamics_reconciliation_error"] = (
            output["observed_debt_ratio_change"] - output["reconstructed_debt_ratio_change"]
        )
        output["primary_balance_contribution_pp"] = output["primary_balance_contribution"] * 100.0
        output["stock_flow_adjustment_pp"] = output["stock_flow_adjustment"] * 100.0
        output["reconstructed_debt_ratio_change_pp"] = (
            output["reconstructed_debt_ratio_change"] * 100.0
        )
        output["debt_dynamics_reconciliation_error_pp"] = (
            output["debt_dynamics_reconciliation_error"] * 100.0
        )
    output.loc[
        ~same_basis,
        [
            "interest_growth_differential",
            "interest_growth_differential_pct",
            "debt_stabilising_primary_balance_before_sfa",
            "debt_stabilising_primary_balance_before_sfa_pct_gdp",
            "observed_debt_ratio_change",
            "observed_debt_ratio_change_pp",
            "interest_growth_contribution",
            "interest_growth_contribution_pp",
            "primary_balance_contribution",
            "primary_balance_contribution_pp",
            "stock_flow_adjustment",
            "stock_flow_adjustment_pp",
            "reconstructed_debt_ratio_change",
            "reconstructed_debt_ratio_change_pp",
            "debt_dynamics_reconciliation_error",
            "debt_dynamics_reconciliation_error_pp",
        ],
    ] = np.nan

    output["interest_eur"] = output["interest_mio_eur"] * 1_000_000.0
    if "government_expenditure_mio_eur" in output.columns:
        output["government_expenditure_eur"] = (
            output["government_expenditure_mio_eur"] * 1_000_000.0
        )
    if "government_revenue_mio_eur" in output.columns:
        output["government_revenue_eur"] = output["government_revenue_mio_eur"] * 1_000_000.0
    output["debt_eur"] = output["debt_mio_eur"] * 1_000_000.0
    output["nominal_gdp_eur"] = output["nominal_gdp_mio_eur"] * 1_000_000.0

    if regime_boundaries:
        output["regime"] = output["year"].map(
            lambda year: assign_regime(int(year), regime_boundaries)
        )

    output["source"] = output.get("source", "Eurostat")
    output["accounting_basis"] = output.get("accounting_basis", "ESA2010")
    output["observation_status"] = output.get("observation_status", "observed")
    numeric_columns = output.select_dtypes(include=[np.number]).columns
    output.loc[:, numeric_columns] = output.loc[:, numeric_columns].mask(
        np.isinf(output.loc[:, numeric_columns]),
        np.nan,
    )
    return output
