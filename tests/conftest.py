"""Shared test helpers.

Several test modules hand-build analytical frames rather than running the
metrics layer, so that expected values can be written by hand. Those frames
still have to carry the debt-dynamics identity columns that
``calculate_metrics`` always produces, otherwise they are testing an input the
pipeline never emits. This helper reproduces those columns with the same
formulas the metrics layer uses.
"""

from __future__ import annotations

import pandas as pd


def add_debt_dynamics_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach the debt-dynamics terms `calculate_metrics` always produces.

    The interest-growth contribution and the debt-stabilising primary balance
    both use the debt-dynamics rate ``I_t / D_{t-1}``, never the average-debt
    descriptive rate.
    """
    output = frame.copy()
    previous_debt = output["debt_mio_eur"].shift(1)
    output["debt_dynamics_interest_rate"] = output["interest_mio_eur"] / previous_debt
    output["debt_dynamics_interest_rate_pct"] = output["debt_dynamics_interest_rate"] * 100.0

    debt_ratio = output["debt_pct_gdp"] / 100.0
    debt_ratio_lag = debt_ratio.shift(1)
    growth = output["nominal_gdp_growth_pct"] / 100.0
    contribution = (
        ((output["debt_dynamics_interest_rate"] - growth) / (1.0 + growth)) * debt_ratio_lag * 100.0
    )

    output["interest_growth_contribution_pp"] = contribution
    output["debt_stabilising_primary_balance_before_sfa_pct_gdp"] = contribution
    output["observed_debt_ratio_change_pp"] = (debt_ratio - debt_ratio_lag) * 100.0
    output["primary_balance_contribution_pp"] = -output["primary_balance_pct_gdp"]
    output["stock_flow_adjustment_pp"] = (
        output["observed_debt_ratio_change_pp"]
        - output["interest_growth_contribution_pp"]
        - output["primary_balance_contribution_pp"]
    )
    output["reconstructed_debt_ratio_change_pp"] = (
        output["interest_growth_contribution_pp"]
        + output["primary_balance_contribution_pp"]
        + output["stock_flow_adjustment_pp"]
    )
    output["debt_dynamics_reconciliation_error_pp"] = (
        output["observed_debt_ratio_change_pp"] - output["reconstructed_debt_ratio_change_pp"]
    )
    return output
