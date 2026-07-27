"""Interest-rate and refinancing counterfactuals."""

from __future__ import annotations

import math

import pandas as pd


def _validate_refinancing_shares(refinancing_shares: list[float]) -> None:
    if any(not math.isfinite(share) for share in refinancing_shares):
        raise ValueError("refinancing shares must be finite")
    if any(share < 0 or share > 1 for share in refinancing_shares):
        raise ValueError("refinancing shares must lie between zero and one")
    if sum(refinancing_shares) > 1.0:
        raise ValueError("refinancing shares must not exceed the outstanding stock")


def _validate_positive_debt(value: float, label: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be positive")


def static_rate_shock_table(
    latest_debt_pct_gdp: float,
    shocks_bps: list[int],
) -> pd.DataFrame:
    """Calculate the long-run full-pass-through burden of rate shocks.

    A 100 basis-point shock applied to a debt stock equal to 90% of GDP has a
    long-run arithmetic effect of 0.9 percentage points of GDP. This is not a
    one-year forecast because only part of the debt stock is refinanced each year.
    """
    _validate_positive_debt(latest_debt_pct_gdp, "latest_debt_pct_gdp")
    rows: list[dict[str, float | int | str]] = []
    for shock in shocks_bps:
        shock_rate = shock / 10_000.0
        rows.append(
            {
                "scenario_kind": "static_full_pass_through",
                "baseline_debt_pct_gdp": latest_debt_pct_gdp,
                "shock_bps": shock,
                "shock_rate_decimal": shock_rate,
                "additional_interest_pct_gdp_full_pass_through": latest_debt_pct_gdp
                * shock_rate,
                "interpretation": "long-run arithmetic simulation",
            }
        )
    return pd.DataFrame(rows)


def refinancing_pass_through(
    initial_interest_pct_gdp: float,
    debt_pct_gdp: float,
    shock_bps: int,
    refinancing_shares: list[float],
) -> pd.DataFrame:
    """Simulate a gradual pass-through through annual refinancing shares."""
    _validate_positive_debt(debt_pct_gdp, "debt_pct_gdp")
    _validate_refinancing_shares(refinancing_shares)
    cumulative_share = 0.0
    rows: list[dict[str, float | int | str]] = []
    full_effect = debt_pct_gdp * (shock_bps / 10_000.0)
    for horizon, share in enumerate(refinancing_shares, start=1):
        cumulative_share += share
        additional = full_effect * cumulative_share
        rows.append(
            {
                "scenario_kind": "dynamic_refinancing",
                "baseline_interest_pct_gdp": initial_interest_pct_gdp,
                "baseline_debt_pct_gdp": debt_pct_gdp,
                "shock_bps": shock_bps,
                "horizon_year": horizon,
                "refinancing_share": share,
                "refinanced_share_cumulative": cumulative_share,
                "additional_interest_pct_gdp": additional,
                "interest_pct_gdp_scenario": initial_interest_pct_gdp + additional,
                "interpretation": "deterministic arithmetic simulation",
            }
        )
    return pd.DataFrame(rows)


def refinancing_path_from_gdp(
    initial_interest_mio_eur: float,
    debt_stock_mio_eur: float,
    shock_bps: int,
    refinancing_shares: list[float],
    nominal_gdp_path_mio_eur: list[float],
) -> pd.DataFrame:
    """Simulate refinancing pass-through with an explicit nominal GDP path."""
    _validate_positive_debt(debt_stock_mio_eur, "debt_stock_mio_eur")
    if len(refinancing_shares) != len(nominal_gdp_path_mio_eur):
        raise ValueError("refinancing shares and GDP path must have the same length")
    if any(not math.isfinite(value) or value <= 0 for value in nominal_gdp_path_mio_eur):
        raise ValueError("nominal GDP path must contain positive values")
    _validate_refinancing_shares(refinancing_shares)

    cumulative_share = 0.0
    cumulative_additional_interest_mio_eur = 0.0
    rows: list[dict[str, float | int | str]] = []
    shock_rate = shock_bps / 10_000.0
    for horizon, (share, gdp_mio_eur) in enumerate(
        zip(refinancing_shares, nominal_gdp_path_mio_eur, strict=True),
        start=1,
    ):
        cumulative_share += share
        additional_interest_mio_eur = debt_stock_mio_eur * shock_rate * cumulative_share
        cumulative_additional_interest_mio_eur += additional_interest_mio_eur
        rows.append(
            {
                "scenario_kind": "dynamic_refinancing",
                "horizon_year": horizon,
                "shock_bps": shock_bps,
                "refinancing_share": share,
                "refinanced_share_cumulative": cumulative_share,
                "nominal_gdp_mio_eur": gdp_mio_eur,
                "additional_interest_mio_eur": additional_interest_mio_eur,
                "cumulative_additional_interest_mio_eur": (
                    cumulative_additional_interest_mio_eur
                ),
                "interest_mio_eur_scenario": initial_interest_mio_eur
                + additional_interest_mio_eur,
                "additional_interest_pct_gdp": additional_interest_mio_eur
                / gdp_mio_eur
                * 100.0,
                "interpretation": "deterministic arithmetic simulation",
            }
        )
    return pd.DataFrame(rows)


def comparator_rate_counterfactual(
    debt_pct_gdp: pd.Series,
    portugal_implicit_rate_pct: pd.Series,
    comparator_implicit_rate_pct: pd.Series,
) -> pd.Series:
    """Estimate the GDP burden at a comparator's effective interest rate."""
    del portugal_implicit_rate_pct  # retained in the signature for transparent comparisons
    return debt_pct_gdp * comparator_implicit_rate_pct / 100.0
