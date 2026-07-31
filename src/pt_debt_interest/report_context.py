"""Generated numerical context consumed by the paper.

Every number the report states in prose has to come from the analytical
dataset rather than being typed into LaTeX. This module builds the canonical
context objects and writes them to ``reports/generated`` so that the report
macros, the tests, and the audit all read the same computed values.

Internally the analytical dataset stores decimal ratios. Percentages and
percentage points are produced only here, at the reporting boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from .exceptions import ValidationError

DEBT_DYNAMICS_CONTEXT_FILENAME: Final[str] = "debt_dynamics_context.json"

#: Years the report discusses individually in the debt-dynamics section.
DEFAULT_FOCUS_YEARS: Final[tuple[int, ...]] = (2020, 2022, 2023)

REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "year",
        "debt_pct_gdp",
        "nominal_gdp_growth_pct",
        "debt_dynamics_interest_rate",
        "average_debt_interest_rate",
        "interest_growth_contribution_pp",
        "debt_stabilising_primary_balance_before_sfa_pct_gdp",
        "stock_flow_adjustment_pp",
        "debt_dynamics_reconciliation_error_pp",
    }
)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _finite_float(value: object, label: str) -> float:
    numeric = float(value)  # type: ignore[arg-type]
    if not np.isfinite(numeric):
        raise ValidationError(f"debt-dynamics context requires a finite {label}")
    return numeric


def build_debt_dynamics_context(
    frame: pd.DataFrame,
    focus_years: tuple[int, ...] = DEFAULT_FOCUS_YEARS,
) -> dict[str, Any]:
    """Build the canonical debt-dynamics numbers the report quotes.

    The debt-stabilising primary balance and the interest-growth contribution
    are both evaluated on the debt-dynamics rate ``r_dd = I_t / D_{t-1}``, not
    on the average-debt descriptive rate. Both rates are carried into the
    context so that a test can prove which one the reported value came from.
    """
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValidationError(f"debt-dynamics context is missing columns: {sorted(missing)}")

    ordered = frame.sort_values("year").copy()
    ordered["year"] = _numeric(ordered, "year")
    if ordered["year"].isna().any() or ordered["year"].mod(1).ne(0).any():
        raise ValidationError("debt-dynamics context requires whole-number years")
    ordered["year"] = ordered["year"].astype(int)
    ordered["lagged_debt_pct_gdp"] = _numeric(ordered, "debt_pct_gdp").shift(1)

    by_year = ordered.set_index("year")
    focus: dict[str, dict[str, float]] = {}
    for year in focus_years:
        if year not in by_year.index:
            raise ValidationError(f"debt-dynamics context requires year {year}")
        row = by_year.loc[year]
        focus[str(year)] = {
            "interest_growth_contribution_pp": _finite_float(
                row["interest_growth_contribution_pp"],
                f"interest-growth contribution for {year}",
            ),
            "debt_stabilising_primary_balance_before_sfa_pct_gdp": _finite_float(
                row["debt_stabilising_primary_balance_before_sfa_pct_gdp"],
                f"debt-stabilising primary balance for {year}",
            ),
            "stock_flow_adjustment_pp": _finite_float(
                row["stock_flow_adjustment_pp"], f"stock-flow adjustment for {year}"
            ),
            "debt_dynamics_interest_rate_pct": _finite_float(
                row["debt_dynamics_interest_rate"] * 100.0,
                f"debt-dynamics rate for {year}",
            ),
            "average_debt_interest_rate_pct": _finite_float(
                row["average_debt_interest_rate"] * 100.0,
                f"average-debt rate for {year}",
            ),
            "nominal_gdp_growth_pct": _finite_float(
                row["nominal_gdp_growth_pct"], f"nominal growth for {year}"
            ),
            "lagged_debt_pct_gdp": _finite_float(
                row["lagged_debt_pct_gdp"], f"lagged debt ratio for {year}"
            ),
        }

    stock_flow = _numeric(ordered.set_index("year"), "stock_flow_adjustment_pp").dropna()
    if stock_flow.empty:
        raise ValidationError("debt-dynamics context requires stock-flow adjustments")

    errors = _numeric(ordered, "debt_dynamics_reconciliation_error_pp").abs().dropna()
    if errors.empty:
        raise ValidationError("debt-dynamics context requires reconciliation errors")

    return {
        "sample": {
            "first_year": int(ordered["year"].min()),
            "last_year": int(ordered["year"].max()),
            "observations": len(ordered),
        },
        "rate_definitions": {
            "debt_dynamics_rate": "I_t / D_{t-1}",
            "average_debt_rate": "I_t / ((D_{t-1} + D_t) / 2)",
            "identity_rate_used": "debt_dynamics_rate",
        },
        "focus_years": focus,
        "stock_flow_adjustment": {
            "minimum_pp": _finite_float(stock_flow.min(), "minimum stock-flow value"),
            "minimum_year": int(stock_flow.idxmin()),
            "maximum_pp": _finite_float(stock_flow.max(), "maximum stock-flow value"),
            "maximum_year": int(stock_flow.idxmax()),
        },
        "reconciliation": {
            "maximum_absolute_error_pp": _finite_float(errors.max(), "maximum reconciliation error")
        },
    }


def write_debt_dynamics_context(
    frame: pd.DataFrame,
    output_dir: Path,
    focus_years: tuple[int, ...] = DEFAULT_FOCUS_YEARS,
) -> Path:
    """Write the debt-dynamics context to ``reports/generated``."""
    context = build_debt_dynamics_context(frame, focus_years)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / DEBT_DYNAMICS_CONTEXT_FILENAME
    path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_debt_dynamics_context(context_dir: Path) -> dict[str, Any]:
    """Read a previously generated debt-dynamics context."""
    path = context_dir / DEBT_DYNAMICS_CONTEXT_FILENAME
    if not path.is_file():
        raise ValidationError(f"debt-dynamics context has not been generated: {path}")
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded
