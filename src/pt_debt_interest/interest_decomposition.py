"""Exact decompositions of the interest burden."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .exceptions import ValidationError

REQUIRED_COLUMNS = {
    "year",
    "interest_mio_eur",
    "implicit_interest_rate_average_debt_decimal",
    "debt_mio_eur",
    "nominal_gdp_mio_eur",
}


def build_interest_burden_decomposition(frame: pd.DataFrame) -> pd.DataFrame:
    """Decompose changes in interest-to-GDP into rate and debt-stock terms.

    The identity is exact:

        Delta(r * b) = Delta(r) * b[-1] + r[-1] * Delta(b) + Delta(r) * Delta(b)

    where r is the average-debt implicit interest rate in decimal form and b is
    average debt divided by nominal GDP. The decomposed burden is reconstructed
    from euro interest and euro GDP so the identity is not contaminated by
    rounded official percentage ratios. Outputs are percentage points of GDP.
    """
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValidationError(
            f"interest-burden decomposition is missing columns: {sorted(missing)}"
        )
    ordered = frame.sort_values("year").copy()
    for column in REQUIRED_COLUMNS:
        ordered[column] = pd.to_numeric(ordered[column], errors="coerce")
    invalid_key = ordered["year"].isna() | ordered["year"].mod(1).ne(0)
    if invalid_key.any():
        raise ValidationError("interest-burden decomposition requires whole-number years")
    average_debt = (ordered["debt_mio_eur"].shift(1) + ordered["debt_mio_eur"]) / 2.0
    average_debt_ratio = average_debt / ordered["nominal_gdp_mio_eur"]
    rate = ordered["implicit_interest_rate_average_debt_decimal"]
    burden = ordered["interest_mio_eur"] / ordered["nominal_gdp_mio_eur"] * 100.0

    lag_rate = rate.shift(1)
    lag_ratio = average_debt_ratio.shift(1)
    delta_rate = rate - lag_rate
    delta_ratio = average_debt_ratio - lag_ratio
    burden_change = burden - burden.shift(1)

    result = pd.DataFrame(
        {
            "year": ordered["year"].astype(int),
            "calculated_interest_burden_pct_gdp": burden,
            "lag_calculated_interest_burden_pct_gdp": burden.shift(1),
            "average_debt_ratio_pct_gdp": average_debt_ratio * 100.0,
            "lag_average_debt_ratio_pct_gdp": lag_ratio * 100.0,
            "average_debt_rate_decimal": rate,
            "lag_average_debt_rate_decimal": lag_rate,
            "calculated_interest_burden_change_pp": burden_change,
            "rate_effect_pp": delta_rate * lag_ratio * 100.0,
            "average_debt_ratio_effect_pp": lag_rate * delta_ratio * 100.0,
            "interaction_effect_pp": delta_rate * delta_ratio * 100.0,
        }
    )
    components = [
        "rate_effect_pp",
        "average_debt_ratio_effect_pp",
        "interaction_effect_pp",
    ]
    result["reconstructed_interest_burden_change_pp"] = result[components].sum(
        axis=1,
        min_count=len(components),
    )
    result["interest_burden_decomposition_residual_pp"] = (
        result["calculated_interest_burden_change_pp"]
        - result["reconstructed_interest_burden_change_pp"]
    )
    result.loc[
        ~np.isfinite(result["interest_burden_decomposition_residual_pp"]),
        "interest_burden_decomposition_residual_pp",
    ] = np.nan
    return result.reset_index(drop=True)
