"""Interest-rate and refinancing counterfactuals."""

from __future__ import annotations

import pandas as pd


def static_rate_shock_table(
    latest_debt_pct_gdp: float,
    shocks_bps: list[int],
) -> pd.DataFrame:
    """Calculate the long-run full-pass-through burden of rate shocks.

    A 100 basis-point shock applied to a debt stock equal to 90% of GDP has a
    long-run arithmetic effect of 0.9 percentage points of GDP. This is not a
    one-year forecast because only part of the debt stock is refinanced each year.
    """
    rows = []
    for shock in shocks_bps:
        shock_rate = shock / 10_000.0
        rows.append(
            {
                "shock_bps": shock,
                "additional_interest_pct_gdp_full_pass_through": latest_debt_pct_gdp
                * shock_rate,
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
    cumulative_share = 0.0
    rows: list[dict[str, float | int]] = []
    full_effect = debt_pct_gdp * (shock_bps / 10_000.0)
    for horizon, share in enumerate(refinancing_shares, start=1):
        cumulative_share = min(1.0, cumulative_share + share)
        additional = full_effect * cumulative_share
        rows.append(
            {
                "horizon_year": horizon,
                "refinanced_share_cumulative": cumulative_share,
                "additional_interest_pct_gdp": additional,
                "interest_pct_gdp_scenario": initial_interest_pct_gdp + additional,
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
