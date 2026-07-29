"""Exact decompositions of the interest burden."""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from .exceptions import ValidationError

DEFAULT_DECOMPOSITION_INTERVALS: Final[tuple[tuple[int, int], ...]] = (
    (1996, 2000),
    (2000, 2007),
    (2007, 2014),
    (2014, 2019),
    (2019, 2022),
    (2022, 2025),
    (2014, 2025),
    (1996, 2025),
)

REQUIRED_COLUMNS = {
    "year",
    "interest_mio_eur",
    "average_debt_interest_rate",
    "debt_mio_eur",
    "nominal_gdp_mio_eur",
}


def _row_int(row: Any, column: str) -> int:
    return int(getattr(row, column))


def _row_float(row: Any, column: str) -> float:
    return float(getattr(row, column))


def build_interest_burden_decomposition_inputs(frame: pd.DataFrame) -> pd.DataFrame:
    """Build annual unrounded inputs used by endpoint decompositions."""
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
    rate = ordered["average_debt_interest_rate"]
    burden = ordered["interest_mio_eur"] / ordered["nominal_gdp_mio_eur"]
    official_burden = (
        pd.to_numeric(ordered["interest_pct_gdp"], errors="coerce") / 100.0
        if "interest_pct_gdp" in ordered.columns
        else burden
    )

    return pd.DataFrame(
        {
            "year": ordered["year"].astype(int),
            "reconstructed_interest_burden": burden,
            "reconstructed_interest_burden_pct_gdp": burden * 100.0,
            "official_interest_burden_pct_gdp": official_burden * 100.0,
            "average_debt_ratio": average_debt_ratio,
            "average_debt_ratio_pct_gdp": average_debt_ratio * 100.0,
            "average_debt_rate": rate,
            "average_debt_rate_pct": rate * 100.0,
        }
    ).reset_index(drop=True)


def build_interest_burden_decomposition(
    frame: pd.DataFrame,
    intervals: tuple[tuple[int, int], ...] = DEFAULT_DECOMPOSITION_INTERVALS,
) -> pd.DataFrame:
    """Build exact two-component endpoint decompositions.

    The symmetric identity is exact:

        b_1 - b_0 =
            ((d_1 + d_0) / 2) * (r_1 - r_0)
            + ((r_1 + r_0) / 2) * (d_1 - d_0)

    where b is reconstructed interest burden, r is the average-debt interest
    rate, and d is average debt divided by nominal GDP. All internal values are
    decimal ratios; published decomposition effects are percentage points.
    """
    annual = build_interest_burden_decomposition_inputs(frame)
    annual = annual.dropna(
        subset=[
            "reconstructed_interest_burden",
            "average_debt_ratio",
            "average_debt_rate",
        ]
    )
    by_year = {_row_int(row, "year"): row for row in annual.itertuples()}
    rows: list[dict[str, float | int | str]] = []
    for start_year, end_year in intervals:
        if start_year not in by_year or end_year not in by_year:
            raise ValidationError(
                "interest-burden endpoint decomposition missing endpoint "
                f"{start_year} or {end_year}"
            )
        start = by_year[start_year]
        end = by_year[end_year]
        start_burden = _row_float(start, "reconstructed_interest_burden")
        end_burden = _row_float(end, "reconstructed_interest_burden")
        start_rate = _row_float(start, "average_debt_rate")
        end_rate = _row_float(end, "average_debt_rate")
        start_exposure = _row_float(start, "average_debt_ratio")
        end_exposure = _row_float(end, "average_debt_ratio")
        total_change = end_burden - start_burden
        rate_effect = ((end_exposure + start_exposure) / 2.0) * (end_rate - start_rate)
        debt_exposure_effect = ((end_rate + start_rate) / 2.0) * (
            end_exposure - start_exposure
        )
        reconciliation_error = total_change - rate_effect - debt_exposure_effect
        dominant = (
            "rate"
            if abs(rate_effect) > abs(debt_exposure_effect)
            else "debt_exposure"
            if abs(debt_exposure_effect) > abs(rate_effect)
            else "tie"
        )
        rows.append(
            {
                "start_year": start_year,
                "end_year": end_year,
                "start_reconstructed_burden_pct_gdp": start_burden * 100.0,
                "end_reconstructed_burden_pct_gdp": end_burden * 100.0,
                "total_change_pp": total_change * 100.0,
                "rate_effect_pp": rate_effect * 100.0,
                "debt_exposure_effect_pp": debt_exposure_effect * 100.0,
                "decomposition_reconciliation_error_pp": reconciliation_error * 100.0,
                "dominant_effect": dominant,
                "official_start_burden_pct_gdp": _row_float(
                    start, "official_interest_burden_pct_gdp"
                ),
                "official_end_burden_pct_gdp": _row_float(
                    end, "official_interest_burden_pct_gdp"
                ),
                "official_reconstructed_difference_start_pp": _row_float(
                    start, "official_interest_burden_pct_gdp"
                )
                - start_burden * 100.0,
                "official_reconstructed_difference_end_pp": _row_float(
                    end, "official_interest_burden_pct_gdp"
                )
                - end_burden * 100.0,
            }
        )
    return pd.DataFrame(rows)


def build_interest_burden_counterfactuals(
    frame: pd.DataFrame,
    start_year: int = 2014,
    end_year: int = 2025,
) -> pd.DataFrame:
    """Build arithmetic cross-rate and cross-exposure burden counterfactuals."""
    annual = build_interest_burden_decomposition_inputs(frame)
    annual = annual.dropna(subset=["average_debt_ratio", "average_debt_rate"])
    by_year = {_row_int(row, "year"): row for row in annual.itertuples()}
    if start_year not in by_year or end_year not in by_year:
        raise ValidationError(
            f"interest-burden counterfactuals require {start_year} and {end_year}"
        )
    start = by_year[start_year]
    end = by_year[end_year]
    start_rate = _row_float(start, "average_debt_rate")
    end_rate = _row_float(end, "average_debt_rate")
    start_exposure = _row_float(start, "average_debt_ratio")
    end_exposure = _row_float(end, "average_debt_ratio")
    values = [
        (
            start_year,
            "observed",
            start_rate,
            start_exposure,
            start_rate * start_exposure,
        ),
        (
            end_year,
            "observed",
            end_rate,
            end_exposure,
            end_rate * end_exposure,
        ),
        (
            start_year,
            f"rate_{start_year}_with_exposure_{end_year}",
            start_rate,
            end_exposure,
            start_rate * end_exposure,
        ),
        (
            end_year,
            f"rate_{end_year}_with_exposure_{start_year}",
            end_rate,
            start_exposure,
            end_rate * start_exposure,
        ),
    ]
    return pd.DataFrame(
        [
            {
                "year": year,
                "counterfactual": label,
                "average_debt_rate": rate,
                "average_debt_exposure": exposure,
                "interest_burden_pct_gdp": burden * 100.0,
                "interpretation": "arithmetic counterfactual, not a causal estimate",
            }
            for year, label, rate, exposure, burden in values
        ]
    )


def validate_decomposition_reconciliation(
    decomposition: pd.DataFrame,
    tolerance: float = 1e-10,
) -> None:
    """Raise when any configured interval fails the exact decomposition identity."""
    if "decomposition_reconciliation_error_pp" not in decomposition.columns:
        raise ValidationError("decomposition output lacks reconciliation errors")
    errors = pd.to_numeric(
        decomposition["decomposition_reconciliation_error_pp"],
        errors="coerce",
    ).abs()
    invalid = errors.isna() | ~np.isfinite(errors) | errors.gt(tolerance)
    if invalid.any():
        intervals = decomposition.loc[invalid, ["start_year", "end_year"]].to_dict(
            orient="records"
        )
        raise ValidationError(f"interest-burden decomposition failed: {intervals}")
