"""Pass-through simulation and out-of-sample backtest.

Two fixes to the burden paper's scenario section are built in.

**Nominal GDP is not held fixed.** The burden paper freezes GDP and the debt
ratio across a ten-year horizon, which contradicts its own finding that the
denominator did most of the work in 2022-2025. Growth paths are explicit here.

**The stock is not homogeneous.** The kernel differentiates instrument classes,
and that differentiation is preserved through the simulation rather than
collapsed to an aggregate hazard at the last step.

Everything is reported as a difference against the zero-shock baseline. Plotting
total burden paths would confound the shock with the starting level.

This is a simulation under an estimated kernel whose behavioural component is a
measured null. It is not a forecast.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from pt_debt_interest.exceptions import ValidationError

from .kernel import KernelInputs, build_kernel, geometric_kernel

#: Nominal growth paths. Zero is retained purely for comparability with the
#: burden paper's implicit assumption; it is not a plausible central case.
GROWTH_PATHS: Final[dict[str, float]] = {
    "zero_growth": 0.0,
    "low": 0.02,
    "central": 0.04,
}

SHOCKS_BPS: Final[tuple[int, ...]] = (-200, -100, -50, 0, 50, 100, 200)
HORIZON_YEARS: Final[int] = 10


def simulate_paths(
    inputs: KernelInputs,
    initial_rate_pct: float,
    debt_pct_gdp: float,
    nominal_gdp_mio_eur: float,
    behavioural_response: float = 0.0,
    shocks_bps: tuple[int, ...] = SHOCKS_BPS,
    growth_paths: dict[str, float] | None = None,
    horizon_years: int = HORIZON_YEARS,
) -> pd.DataFrame:
    """Evolve the effective rate and burden under each shock and growth path."""
    paths = growth_paths if growth_paths is not None else GROWTH_PATHS
    horizons = tuple(range(1, horizon_years + 1))

    baseline = {
        name: build_kernel(inputs, 0, behavioural_response, horizons)["repriced_share"]
        .to_numpy()
        for name in ("kernel",)
    }["kernel"]

    rows: list[dict[str, object]] = []
    for growth_name, growth in paths.items():
        for shock in shocks_bps:
            repriced = build_kernel(
                inputs, shock, behavioural_response, horizons
            )["repriced_share"].to_numpy()
            shock_pct = shock / 100.0

            # Effective rate: the repriced portion carries the shocked rate.
            rate = initial_rate_pct + repriced * shock_pct
            baseline_rate = initial_rate_pct + baseline * 0.0

            # The denominator moves. This is the burden paper's fixed-GDP flaw.
            years = np.asarray(horizons, dtype=float)
            gdp = nominal_gdp_mio_eur * (1.0 + growth) ** years
            debt_ratio = debt_pct_gdp * (nominal_gdp_mio_eur / gdp)

            burden = rate * debt_ratio / 100.0
            baseline_burden = baseline_rate * debt_ratio / 100.0
            interest = burden / 100.0 * gdp
            baseline_interest = baseline_burden / 100.0 * gdp

            for index, horizon in enumerate(horizons):
                rows.append(
                    {
                        "growth_path": growth_name,
                        "nominal_growth": growth,
                        "shock_bps": shock,
                        "horizon_years": horizon,
                        "repriced_share": repriced[index],
                        "effective_rate_pct": rate[index],
                        "debt_pct_gdp": debt_ratio[index],
                        "burden_pct_gdp": burden[index],
                        "incremental_burden_pct_gdp": burden[index]
                        - baseline_burden[index],
                        "incremental_interest_mio_eur": interest[index]
                        - baseline_interest[index],
                    }
                )

    frame = pd.DataFrame(rows)
    frame["cumulative_incremental_interest_mio_eur"] = frame.groupby(
        ["growth_path", "shock_bps"]
    )["incremental_interest_mio_eur"].cumsum()
    return frame


def half_life(paths: pd.DataFrame, growth_path: str = "central") -> pd.DataFrame:
    """Horizon at which incremental pass-through reaches half its asymptote."""
    rows: list[dict[str, object]] = []
    window = paths.loc[paths["growth_path"].eq(growth_path)]
    for shock, group in window.groupby("shock_bps"):
        if shock == 0:
            continue
        ordered = group.sort_values("horizon_years")
        asymptote = ordered["incremental_burden_pct_gdp"].abs().max()
        if asymptote == 0:
            continue
        reached = ordered.loc[
            ordered["incremental_burden_pct_gdp"].abs() >= 0.5 * asymptote,
            "horizon_years",
        ]
        rows.append(
            {
                "shock_bps": int(float(str(shock))),
                "asymptote_pct_gdp": float(asymptote),
                "half_life_years": float(reached.iloc[0]) if len(reached) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def backtest(
    burden_frame: pd.DataFrame,
    inputs: KernelInputs,
    cut_year: int = 2021,
    behavioural_response: float = 0.0,
) -> pd.DataFrame:
    """Predict the effective rate after a cut date and score against realised.

    The realised effective rate is **imported** from the burden paper, not
    recomputed, so the two papers cannot drift apart.

    Benchmarks: the weighted-average-maturity constant hazard, immediate full
    pass-through, and a random walk in the effective rate.
    """
    required = {"year", "average_debt_interest_rate_pct", "ten_year_yield_pct"}
    missing = required.difference(burden_frame.columns)
    if missing:
        raise ValidationError(f"backtest requires columns: {sorted(missing)}")

    frame = burden_frame.dropna(subset=sorted(required)).copy()
    frame["year"] = frame["year"].astype(int)
    history = frame.loc[frame["year"] <= cut_year]
    future = frame.loc[frame["year"] > cut_year]
    if history.empty or future.empty:
        raise ValidationError(f"cut year {cut_year} leaves no data on one side")

    anchor = float(history["average_debt_interest_rate_pct"].iloc[-1])
    horizons = tuple(range(1, len(future) + 1))

    estimated = build_kernel(inputs, 0, behavioural_response, horizons)[
        "repriced_share"
    ].to_numpy()
    wam = geometric_kernel(
        np.asarray(horizons, dtype=float), inputs.average_residual_maturity_years
    )

    rows: list[dict[str, object]] = []
    for index, row in enumerate(future.itertuples()):
        # Realised issuance yields are fed in, so kernel error is isolable.
        issuance = float(str(row.ten_year_yield_pct))
        realised = float(str(row.average_debt_interest_rate_pct))
        predictions = {
            "estimated_kernel": anchor + estimated[index] * (issuance - anchor),
            "wam_benchmark": anchor + wam[index] * (issuance - anchor),
            "immediate_full_pass_through": issuance,
            "random_walk": anchor,
        }
        for model, predicted in predictions.items():
            rows.append(
                {
                    "cut_year": cut_year,
                    "year": int(float(str(row.year))),
                    "horizon_years": index + 1,
                    "model": model,
                    "realised_rate_pct": realised,
                    "predicted_rate_pct": predicted,
                    "error_pp": predicted - realised,
                    "absolute_error_bps": abs(predicted - realised) * 100.0,
                }
            )
    return pd.DataFrame(rows)


def backtest_summary(scores: pd.DataFrame) -> pd.DataFrame:
    """Mean absolute error by model, in basis points on the effective rate."""
    summary = (
        scores.groupby(["cut_year", "model"])["absolute_error_bps"]
        .agg(["mean", "max", "size"])
        .reset_index()
        .rename(columns={"mean": "mean_abs_error_bps", "max": "worst_bps", "size": "n"})
    )
    return summary.sort_values(["cut_year", "mean_abs_error_bps"]).reset_index(drop=True)
