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


def assign_regime(year: int, boundaries: list[dict[str, object]]) -> str | None:
    """Return the configured regime label for a year."""
    for boundary in boundaries:
        if int(str(boundary["start"])) <= year <= int(str(boundary["end"])):
            return str(boundary["label"])
    return None


def _validate_percentage_scale(frame: pd.DataFrame) -> None:
    """Detect likely decimal-ratio inputs in persisted percentage columns."""
    if "debt_pct_gdp_official" not in frame.columns:
        return
    debt_ratio = pd.to_numeric(frame["debt_pct_gdp_official"], errors="coerce").dropna()
    if not debt_ratio.empty and debt_ratio.abs().median() <= 2.0:
        raise ValueError("debt_pct_gdp_official must be expressed as a percentage, not a ratio")


def _validate_annual_input(frame: pd.DataFrame) -> None:
    """Reject inputs that make lagged annual calculations ambiguous."""
    if frame["year"].isna().any():
        raise ValueError("annual metrics require non-missing years")
    try:
        pd.to_numeric(frame["year"], errors="raise").astype(int)
    except (TypeError, ValueError) as exc:
        raise ValueError("annual metrics require numeric years") from exc
    duplicate_years = (
        frame.loc[frame["year"].duplicated(keep=False), "year"].dropna().astype(int).tolist()
    )
    if duplicate_years:
        raise ValueError(f"annual metrics require unique years: {duplicate_years}")


def _validate_positive_denominators(frame: pd.DataFrame) -> None:
    """Reject non-positive values used as metric denominators."""
    for column in ["nominal_gdp_mio_eur", "debt_mio_eur"]:
        values = pd.to_numeric(frame[column], errors="coerce")
        affected_years = frame.loc[values.notna() & values.le(0), "year"].astype(int).tolist()
        if affected_years:
            raise ValueError(f"{column} must be positive for years: {affected_years}")


def _validate_growth_factors(frame: pd.DataFrame) -> None:
    """Reject growth values that make factor-based calculations undefined."""
    if "real_gdp_growth_pct" not in frame.columns:
        return
    values = pd.to_numeric(frame["real_gdp_growth_pct"], errors="coerce")
    affected_years = frame.loc[values.notna() & values.le(-100), "year"].astype(int).tolist()
    if affected_years:
        raise ValueError(
            f"real_gdp_growth_pct must be greater than -100 for years: {affected_years}"
        )


def _same_accounting_basis_as_previous(output: pd.DataFrame) -> pd.Series:
    """Return rows whose lagged calculations stay within one accounting basis."""
    if "accounting_basis" not in output.columns:
        return pd.Series(True, index=output.index)
    basis = output["accounting_basis"].astype("string")
    return basis.eq(basis.shift(1)).fillna(False)


def calculate_metrics(
    frame: pd.DataFrame,
    denominator: str = "average_debt",
    regime_boundaries: list[dict[str, object]] | None = None,
) -> pd.DataFrame:
    """Calculate the analytical annual indicators.

    Parameters
    ----------
    frame:
        Annual source data indexed by a `year` column.
    denominator:
        `average_debt` uses the mean of debt at t-1 and t. `previous_debt`
        uses only the debt stock at t-1.
    regime_boundaries:
        Optional list of dictionaries with `start`, `end`, and `label`.
    """
    missing = REQUIRED_BASE_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if denominator not in {"average_debt", "previous_debt"}:
        raise ValueError("unsupported implicit-rate denominator")

    _validate_percentage_scale(frame)
    _validate_annual_input(frame)
    _validate_positive_denominators(frame)
    _validate_growth_factors(frame)

    output = frame.sort_values("year").copy()
    output["interest_pct_gdp_calculated"] = (
        output["interest_mio_eur"] / output["nominal_gdp_mio_eur"] * 100.0
    )
    output["debt_pct_gdp_calculated"] = (
        output["debt_mio_eur"] / output["nominal_gdp_mio_eur"] * 100.0
    )
    same_basis = _same_accounting_basis_as_previous(output)
    output["nominal_gdp_growth_pct"] = output["nominal_gdp_mio_eur"].pct_change() * 100.0
    output.loc[~same_basis, "nominal_gdp_growth_pct"] = np.nan

    previous_debt = output["debt_mio_eur"].shift(1)
    average_debt = (previous_debt + output["debt_mio_eur"]) / 2.0
    output["implicit_interest_rate_previous_debt_pct"] = (
        output["interest_mio_eur"] / previous_debt * 100.0
    )
    output["implicit_interest_rate_average_debt_pct"] = (
        output["interest_mio_eur"] / average_debt * 100.0
    )
    output.loc[~same_basis, "implicit_interest_rate_previous_debt_pct"] = np.nan
    output.loc[~same_basis, "implicit_interest_rate_average_debt_pct"] = np.nan
    selected_rate = (
        "implicit_interest_rate_average_debt_pct"
        if denominator == "average_debt"
        else "implicit_interest_rate_previous_debt_pct"
    )
    output["implicit_interest_rate_pct"] = output[selected_rate]

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

    if "overall_balance_pct_gdp" in output.columns:
        output["primary_balance_pct_gdp"] = (
            output["overall_balance_pct_gdp"] + output["interest_pct_gdp"]
        )

    debt_ratio_lag = output["debt_pct_gdp"].shift(1) / 100.0
    debt_ratio = output["debt_pct_gdp"] / 100.0
    rate = output["implicit_interest_rate_pct"] / 100.0
    growth = output["nominal_gdp_growth_pct"] / 100.0
    output["interest_growth_differential_pct"] = (rate - growth) * 100.0
    output["debt_stabilising_primary_balance_pct_gdp"] = (
        ((rate - growth) / (1.0 + growth)) * debt_ratio_lag * 100.0
    )
    if "primary_balance_pct_gdp" in output.columns:
        debt_change_pct_gdp = (debt_ratio - debt_ratio_lag) * 100.0
        automatic_debt_dynamics = (
            ((rate - growth) / (1.0 + growth)) * debt_ratio_lag * 100.0
        )
        output["stock_flow_adjustment_pct_gdp"] = (
            debt_change_pct_gdp
            - automatic_debt_dynamics
            + output["primary_balance_pct_gdp"]
        )
    output.loc[
        ~same_basis,
        [
            "interest_growth_differential_pct",
            "debt_stabilising_primary_balance_pct_gdp",
            "stock_flow_adjustment_pct_gdp",
        ],
    ] = np.nan

    output["interest_eur"] = output["interest_mio_eur"] * 1_000_000.0
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
