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
        if int(boundary["start"]) <= year <= int(boundary["end"]):
            return str(boundary["label"])
    return None


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

    output = frame.sort_values("year").copy()
    output["interest_pct_gdp_calculated"] = (
        output["interest_mio_eur"] / output["nominal_gdp_mio_eur"] * 100.0
    )
    output["debt_pct_gdp_calculated"] = (
        output["debt_mio_eur"] / output["nominal_gdp_mio_eur"] * 100.0
    )
    output["nominal_gdp_growth_pct"] = output["nominal_gdp_mio_eur"].pct_change() * 100.0

    previous_debt = output["debt_mio_eur"].shift(1)
    if denominator == "average_debt":
        debt_denominator = (previous_debt + output["debt_mio_eur"]) / 2.0
    else:
        debt_denominator = previous_debt
    output["implicit_interest_rate_pct"] = (
        output["interest_mio_eur"] / debt_denominator * 100.0
    )

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
    return output.replace([np.inf, -np.inf], np.nan)
