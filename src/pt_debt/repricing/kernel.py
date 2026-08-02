"""The repricing kernel: share of the opening stock repriced by horizon h.

Three components, combined rather than conflated:

1. **Contractual.** Debt that matures on schedule. No estimation.
2. **Reset.** Floating-rate and inflation-linked debt reprices without exiting.
   Not a survival event; carried on its own track.
3. **Behavioural.** Retail subscriptions onto the prevailing rate. Estimated,
   and the estimate is a null, so its band includes zero by construction.

The kernel is a *function of the shock*, not a scalar. That is the whole point:
the burden paper's kernel is a constant hazard calibrated to published weighted
average maturity, and this one is not.

On the shape counterfactual
---------------------------
A memoryless hazard with mean maturity ``m`` leaves ``exp(-h/m)`` unrepriced at
horizon ``h`` — a long right tail. A real redemption profile with the *same
mean* retires far more by ``h``. Since no dated schedule is published (see
``docs/manual_ingest.md``), the contrast uses a linear retirement profile with
the same mean, which is a stylised standard shape and **not** IGCP's actual
schedule. That substitution is stated wherever the shape bias is reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import numpy as np
import pandas as pd

from pt_debt_interest.exceptions import ValidationError

DEFAULT_HORIZONS: Final[tuple[int, ...]] = (1, 3, 5, 10)

#: Floating and inflation-linked debt reprices on its own cycle, taken as
#: annual. Faster than any maturity-driven exit.
RESET_CYCLE_YEARS: Final[float] = 1.0


@dataclass(frozen=True)
class KernelInputs:
    """Portfolio state at the horizon origin."""

    average_residual_maturity_years: float
    fixed_rate_share: float
    retail_share_of_stock: float

    def __post_init__(self) -> None:
        if self.average_residual_maturity_years <= 0:
            raise ValidationError("average residual maturity must be positive")
        for name, value in (
            ("fixed_rate_share", self.fixed_rate_share),
            ("retail_share_of_stock", self.retail_share_of_stock),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{name} must lie in [0, 1]")


def geometric_kernel(
    horizons: np.ndarray[Any, Any], mean_maturity_years: float
) -> np.ndarray[Any, Any]:
    """The weighted-average-maturity benchmark: a memoryless hazard.

    This is exactly the burden paper's assumption, and the object this paper
    argues is biased.
    """
    return 1.0 - np.exp(-horizons / mean_maturity_years)


def linear_profile_kernel(
    horizons: np.ndarray[Any, Any], mean_maturity_years: float
) -> np.ndarray[Any, Any]:
    """A stylised redemption profile with the same mean, retiring linearly.

    Everything is retired by twice the mean maturity, which is what a uniform
    retirement schedule with mean ``m`` implies. Stylised, not IGCP's schedule.
    """
    horizon_to_full = 2.0 * mean_maturity_years
    return np.clip(horizons / horizon_to_full, 0.0, 1.0)


def build_kernel(
    inputs: KernelInputs,
    shock_bps: int = 0,
    behavioural_response: float = 0.0,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    use_shape_profile: bool = True,
) -> pd.DataFrame:
    """Repriced share by horizon, decomposed into its three components.

    ``behavioural_response`` is the monthly repricing response per percentage
    point of spread, from the estimation step. Its estimate is a null, so a
    caller propagating uncertainty will pass values spanning zero.
    """
    grid = np.asarray(horizons, dtype=float)
    floating_share = 1.0 - inputs.fixed_rate_share

    contractual_base = (
        linear_profile_kernel(grid, inputs.average_residual_maturity_years)
        if use_shape_profile
        else geometric_kernel(grid, inputs.average_residual_maturity_years)
    )
    # Only the fixed-rate, non-retail portion reprices by maturing.
    maturity_track = inputs.fixed_rate_share - inputs.retail_share_of_stock
    contractual = contractual_base * max(maturity_track, 0.0)

    # Floating debt reprices on its cycle regardless of the shock.
    reset = floating_share * np.clip(grid / RESET_CYCLE_YEARS, 0.0, 1.0)

    # The behavioural track responds to the shock. A zero response leaves the
    # retail block repricing only as fast as its contractual base.
    spread_pp = shock_bps / 100.0
    monthly_boost = behavioural_response * spread_pp
    behavioural_rate = np.clip(monthly_boost * 12.0 * grid, 0.0, 1.0)
    behavioural_base = linear_profile_kernel(grid, inputs.average_residual_maturity_years)
    behavioural = inputs.retail_share_of_stock * np.clip(
        behavioural_base + behavioural_rate, 0.0, 1.0
    )

    total = np.clip(contractual + reset + behavioural, 0.0, 1.0)
    return pd.DataFrame(
        {
            "horizon_years": grid.astype(int),
            "shock_bps": shock_bps,
            "contractual_share": contractual,
            "reset_share": reset,
            "behavioural_share": behavioural,
            "repriced_share": total,
        }
    )


def wam_implied_kernel(
    inputs: KernelInputs, horizons: tuple[int, ...] = DEFAULT_HORIZONS
) -> pd.DataFrame:
    """The benchmark kernel: one constant hazard over the whole stock."""
    grid = np.asarray(horizons, dtype=float)
    return pd.DataFrame(
        {
            "horizon_years": grid.astype(int),
            "repriced_share": geometric_kernel(grid, inputs.average_residual_maturity_years),
        }
    )


def bias_table(
    inputs: KernelInputs,
    shock_bps: int = 100,
    behavioural_response: float = 0.0,
    behavioural_low: float = 0.0,
    behavioural_high: float = 0.0,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> pd.DataFrame:
    """Quantify how wrong the standard approximation is, with a band.

    The bias is decomposed into two mechanisms, separately quantified:

    *Shape* — a memoryless hazard has a long right tail, so it under-retires
    relative to a real profile with the same mean. This exists even with no
    behavioural response at all.

    *Behaviour* — the shock-responsive retail component. Its band comes from the
    estimation, which returned a null, so it spans zero.
    """
    benchmark = wam_implied_kernel(inputs, horizons)["repriced_share"].to_numpy()

    # Shape only: the estimated structure with a zero behavioural response.
    shape_only = build_kernel(inputs, shock_bps=0, behavioural_response=0.0, horizons=horizons)[
        "repriced_share"
    ].to_numpy()

    central = build_kernel(inputs, shock_bps, behavioural_response, horizons)[
        "repriced_share"
    ].to_numpy()
    low = build_kernel(inputs, shock_bps, behavioural_low, horizons)["repriced_share"].to_numpy()
    high = build_kernel(inputs, shock_bps, behavioural_high, horizons)["repriced_share"].to_numpy()

    return pd.DataFrame(
        {
            "horizon_years": list(horizons),
            "wam_implied_share": benchmark,
            "estimated_share": central,
            "estimated_share_low": low,
            "estimated_share_high": high,
            "total_bias_pp": (central - benchmark) * 100.0,
            "shape_bias_pp": (shape_only - benchmark) * 100.0,
            "behaviour_bias_pp": (central - shape_only) * 100.0,
            "behaviour_bias_low_pp": (low - shape_only) * 100.0,
            "behaviour_bias_high_pp": (high - shape_only) * 100.0,
        }
    )


def fiscal_translation(
    bias: pd.DataFrame,
    debt_pct_gdp: float,
    shock_bps: int,
    nominal_gdp_mio_eur: float,
) -> pd.DataFrame:
    """Translate the kernel bias into interest missed or overstated.

    A share of the stock repriced by ``shock_bps`` costs
    ``share * debt_ratio * shock`` in percentage points of GDP.
    """
    shock_rate = shock_bps / 10_000.0
    output = bias.copy()
    output["bias_interest_pct_gdp"] = output["total_bias_pp"] / 100.0 * debt_pct_gdp * shock_rate
    output["bias_interest_mio_eur"] = output["bias_interest_pct_gdp"] / 100.0 * nominal_gdp_mio_eur
    output["shock_bps"] = shock_bps
    return output
