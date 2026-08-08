"""The repricing kernel: share of the opening stock repriced by horizon h.

Three components, combined rather than conflated:

1. **Contractual.** Debt that matures on schedule. No estimation.
2. **Reset.** Floating-rate and inflation-linked debt reprices without exiting.
   Not a survival event; carried on its own track.
3. **Behavioural.** Retail subscriptions onto the prevailing rate. Estimated,
   and the estimate is not identified, so its central value is set to zero
   and its band is reported as a sensitivity.

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

#: How much of a given rate shock the reset block absorbs, per unit of shock.
#:
#: Reset *timing* and shock *loading* are different assumptions and the kernel
#: keeps them separate. One says how often a coupon is refreshed; the other
#: says how much of a policy or market-rate shock that refresh passes through.
#: An inflation-linked coupon can reset annually and still respond to a
#: policy-rate shock quite differently from a Euribor-linked one. The default
#: of one for one is a scenario choice, not an estimate, and the sensitivity
#: grid varies it.
RESET_SHOCK_LOADING: Final[float] = 1.0

#: Series F Savings Certificates are indexed to three-month Euribor, so the
#: retail variable block resets on a quarterly clock rather than the general
#: wholesale one.
RETAIL_RESET_CYCLE_YEARS: Final[float] = 0.25


@dataclass(frozen=True)
class KernelInputs:
    """Portfolio state at the horizon origin.

    ``retail_variable_share`` and ``retail_fixed_share`` split the retail block
    by rate type, which the kernel needs in order to partition the stock into
    mutually exclusive classes. Without them the earlier construction double
    counted: it subtracted *all* retail debt from the fixed-rate track and
    simultaneously treated the *entire* non-fixed residual as a wholesale reset
    block, so Savings Certificates -- which are retail and variable-rate, Series
    F indexed to three-month Euribor -- were removed from a track they were
    never in and counted in another.

    They default to zero, which reproduces the old undifferentiated behaviour
    for callers that have not been updated, but :meth:`partition` refuses to
    produce overlapping classes.
    """

    average_residual_maturity_years: float
    fixed_rate_share: float
    retail_share_of_stock: float
    retail_variable_share: float = 0.0
    retail_fixed_share: float = 0.0

    def __post_init__(self) -> None:
        if self.average_residual_maturity_years <= 0:
            raise ValidationError("average residual maturity must be positive")
        for name, value in (
            ("fixed_rate_share", self.fixed_rate_share),
            ("retail_share_of_stock", self.retail_share_of_stock),
            ("retail_variable_share", self.retail_variable_share),
            ("retail_fixed_share", self.retail_fixed_share),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{name} must lie in [0, 1]")

    def partition(self) -> dict[str, float]:
        """Mutually exclusive opening-stock classes, summing to one.

        =====================  ===========================================
        class                  repricing law
        =====================  ===========================================
        ``wholesale_fixed``    contractual retirement at the portfolio WAM
        ``retail_fixed``       contractual; Treasury Certificates carry a
                               guaranteed schedule and do not capitalise
        ``retail_variable``    reference-formula reset, quarterly for the
                               Series F Euribor indexation
        ``wholesale_floating`` reference-rate reset on the general cycle
        =====================  ===========================================

        Raises when the shares imply a negative class, which happens if the
        retail split is inconsistent with the published fixed-rate share.
        """
        wholesale_fixed = self.fixed_rate_share - self.retail_fixed_share
        wholesale_floating = (
            1.0 - self.fixed_rate_share
        ) - self.retail_variable_share
        classes = {
            "wholesale_fixed": wholesale_fixed,
            "retail_fixed": self.retail_fixed_share,
            "retail_variable": self.retail_variable_share,
            "wholesale_floating": wholesale_floating,
        }
        negative = {name: value for name, value in classes.items() if value < -1e-9}
        if negative:
            raise ValidationError(
                "portfolio partition implies negative classes, so the retail "
                f"split is inconsistent with the fixed-rate share: {negative}"
            )
        return {name: max(value, 0.0) for name, value in classes.items()}


def geometric_kernel(
    horizons: np.ndarray[Any, Any], mean_maturity_years: float
) -> np.ndarray[Any, Any]:
    """The weighted-average-maturity benchmark: a discrete annual hazard.

    This is exactly the burden paper's assumption, and the object this paper
    argues is biased.
    """
    hazard = 1.0 / mean_maturity_years
    return 1.0 - (1.0 - hazard) ** horizons


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
    shock_bps: float = 0.0,
    behavioural_response: float = 0.0,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    use_shape_profile: bool = True,
    reset_cycle_years: float = RESET_CYCLE_YEARS,
    reset_shock_loading: float = RESET_SHOCK_LOADING,
    retail_reset_cycle_years: float = RETAIL_RESET_CYCLE_YEARS,
) -> pd.DataFrame:
    """Repriced share by horizon, decomposed into its three components.

    ``behavioural_response`` is the monthly repricing response per percentage
    point of spread, from the estimation step. The estimate is precise but not
    identified -- the placebo loads -- so the central value used here is zero
    and callers propagating uncertainty pass values spanning it.
    """
    if reset_cycle_years <= 0.0:
        raise ValidationError("reset cycle must be positive")

    grid = np.asarray(horizons, dtype=float)
    classes = inputs.partition()

    contractual_base = (
        linear_profile_kernel(grid, inputs.average_residual_maturity_years)
        if use_shape_profile
        else geometric_kernel(grid, inputs.average_residual_maturity_years)
    )

    # Contractual: debt that reprices only by maturing and being reissued.
    # Both fixed-rate classes belong here and nothing else does. Treasury
    # Certificates carry a guaranteed fixed schedule and do not capitalise, so
    # they retire like wholesale fixed debt rather than resetting.
    contractual = contractual_base * (
        classes["wholesale_fixed"] + classes["retail_fixed"]
    )

    # Reset: debt that receives a new rate without leaving the stock. Series F
    # Savings Certificates are indexed to three-month Euribor and reset on that
    # cycle, which is faster than the general wholesale cycle, so the two
    # variable classes are carried on separate clocks rather than pooled.
    reset = classes["wholesale_floating"] * np.clip(
        grid / reset_cycle_years, 0.0, 1.0
    ) + classes["retail_variable"] * np.clip(
        grid / retail_reset_cycle_years, 0.0, 1.0
    )

    # Behavioural: new retail money arriving on the prevailing rate. This is a
    # flow, not a repricing of the opening stock, so it is additive to the
    # partition rather than carved out of it -- the earlier construction gave
    # the retail block a contractual base of its own, which double counted it
    # against the tracks above.
    spread_pp = shock_bps / 100.0
    monthly_boost = behavioural_response * spread_pp
    # Fall back to the undifferentiated retail share when the split is absent,
    # so a caller that has not supplied it still gets a behavioural block
    # rather than silently losing one.
    retail_stock = (
        classes["retail_variable"] + classes["retail_fixed"]
        or inputs.retail_share_of_stock
    )
    behavioural = retail_stock * np.clip(monthly_boost * 12.0 * grid, 0.0, 1.0)

    total = np.clip(contractual + reset + behavioural, 0.0, 1.0)

    # Physical repricing and shock transmission are not the same quantity. A
    # reset instrument reprices on schedule whatever the loading, but it only
    # passes through the part of the shock its formula tracks. `repriced_share`
    # answers "how much of the stock has a new rate"; `shock_weighted_share`
    # answers "how much of the shock has reached the stock", and a rate
    # translation wants the second. They coincide at unit loading, which is the
    # default, so this column changes no existing result.
    shock_weighted = np.clip(
        contractual + reset * reset_shock_loading + behavioural, 0.0, 1.0
    )
    return pd.DataFrame(
        {
            "horizon_years": grid.astype(int),
            "shock_bps": float(shock_bps),
            "contractual_share": contractual,
            "reset_share": reset,
            "behavioural_share": behavioural,
            "repriced_share": total,
            "shock_weighted_share": shock_weighted,
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


#: Where a manually digitised IGCP refixing profile is expected.
REFIXING_PROFILE_PATH: Final[str] = "data/raw/manual/igcp_refixing_profile.csv"

_REFIXING_COLUMNS: Final[tuple[str, ...]] = (
    "bracket_lower_years",
    "bracket_upper_years",
    "share_of_portfolio",
)


def refixing_comparison(
    profile: pd.DataFrame,
    inputs: KernelInputs,
    *,
    reset_cycle_years: float = RESET_CYCLE_YEARS,
    retail_reset_cycle_years: float = RETAIL_RESET_CYCLE_YEARS,
) -> pd.DataFrame:
    """Compare the imposed kernel shape with IGCP's published refixing profile.

    The kernel's contractual and reset shapes are assumptions, and weighted
    average maturity is a weak comparator for them. IGCP's own risk framework
    publishes a refixing profile -- the share of the adjusted portfolio due to
    refix or mature inside each maturity bracket -- which is the closest
    published object to what this kernel constructs.

    The profile is published as a chart, so it has to be digitised by hand;
    ``docs/manual_ingest.md`` specifies the file. This function exists so the
    comparison runs the moment that file appears rather than waiting on further
    code, and so the absence of the comparison is a missing input rather than a
    missing method.

    Returns one row per bracket with the published share, the share this
    kernel implies over the same bracket, and the difference in percentage
    points.
    """
    missing = [name for name in _REFIXING_COLUMNS if name not in profile.columns]
    if missing:
        raise ValidationError(f"refixing profile is missing columns: {missing}")

    working = profile.copy()
    working["bracket_upper_years"] = working["bracket_upper_years"].fillna(np.inf)

    rows: list[dict[str, object]] = []
    for row in working.itertuples():
        lower = float(str(row.bracket_lower_years))
        upper = float(str(row.bracket_upper_years))
        # Cumulative kernel at each edge; the bracket share is the increment.
        edges = np.array([lower, min(upper, 1.0e6)], dtype=float)
        cumulative = build_kernel(
            inputs,
            horizons=tuple(edges.astype(int)) if (edges % 1 == 0).all() else (1, 2),
            reset_cycle_years=reset_cycle_years,
            retail_reset_cycle_years=retail_reset_cycle_years,
        )
        implied = float(
            cumulative["repriced_share"].iloc[-1] - cumulative["repriced_share"].iloc[0]
        )
        published = float(str(row.share_of_portfolio))
        rows.append(
            {
                "bracket_lower_years": lower,
                "bracket_upper_years": upper,
                "published_share": published,
                "kernel_implied_share": implied,
                "difference_pp": (implied - published) * 100.0,
            }
        )
    return pd.DataFrame(rows)
