"""Pass-through simulation and out-of-sample backtest.

Two fixes to the burden paper's scenario section are built in.

**Nominal GDP is not held fixed in every scenario.** The burden paper freezes
GDP and the debt ratio to isolate refinancing arithmetic. Growth paths are
explicit here so the denominator sensitivity can be inspected rather than
treated as an empirical correction.

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

from .kernel import (
    DEFAULT_HORIZONS,
    KernelInputs,
    build_kernel,
    geometric_kernel,
    wam_implied_kernel,
)

#: Nominal growth paths. Zero is retained purely for comparability with the
#: burden paper's implicit assumption; it is not a plausible central case.
GROWTH_PATHS: Final[dict[str, float]] = {
    "zero_growth": 0.0,
    "low": 0.02,
    "central": 0.04,
}

SHOCKS_BPS: Final[tuple[int, ...]] = (-200, -100, -50, 0, 50, 100, 200)
HORIZON_YEARS: Final[int] = 10
MONTE_CARLO_SEED: Final[int] = 20260806


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

            # The denominator moves in these scenarios; the burden paper's
            # fixed-GDP case remains a ceteris-paribus comparison.
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


def model_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    """Collapse cut-year backtests into a compact model comparison."""
    required = {"cut_year", "model", "mean_abs_error_bps", "worst_bps"}
    missing = required.difference(summary.columns)
    if missing:
        raise ValidationError(f"model comparison requires columns: {sorted(missing)}")

    winners = summary.loc[
        summary.groupby("cut_year")["mean_abs_error_bps"].idxmin(), ["cut_year", "model"]
    ]
    win_counts = winners["model"].value_counts()
    output = (
        summary.groupby("model")
        .agg(
            mean_abs_error_bps=("mean_abs_error_bps", "mean"),
            worst_bps=("worst_bps", "max"),
            cut_years=("cut_year", "nunique"),
        )
        .reset_index()
    )
    output["win_count"] = output["model"].map(win_counts).fillna(0).astype(int)
    return output.sort_values(["mean_abs_error_bps", "model"]).reset_index(drop=True)


def sensitivity_grid(
    inputs: KernelInputs,
    *,
    behavioural_response: float,
    behavioural_low: float,
    behavioural_high: float,
    debt_pct_gdp: float,
    shock_bps: float = 100.0,
    horizons: tuple[int, ...] = (1, 5),
) -> pd.DataFrame:
    """Vary the principal modelling assumptions around the central kernel."""
    scenarios: list[tuple[str, float, bool, float]] = [
        ("central", behavioural_response, True, 1.0),
        ("slow_reset", behavioural_response, True, 2.0),
        ("fast_reset", behavioural_response, True, 0.5),
        ("memoryless_contractual_shape", behavioural_response, False, 1.0),
        ("behaviour_off", 0.0, True, 1.0),
        ("behaviour_lower_bound", behavioural_low, True, 1.0),
        ("behaviour_upper_bound", behavioural_high, True, 1.0),
    ]
    benchmark = wam_implied_kernel(inputs, horizons)["repriced_share"].to_numpy()
    shock_rate = shock_bps / 10_000.0
    rows: list[dict[str, object]] = []
    for scenario, response, use_shape_profile, reset_cycle_years in scenarios:
        kernel = build_kernel(
            inputs,
            shock_bps=shock_bps,
            behavioural_response=response,
            horizons=horizons,
            use_shape_profile=use_shape_profile,
            reset_cycle_years=reset_cycle_years,
        )
        repriced = kernel["repriced_share"].to_numpy()
        for index, horizon in enumerate(horizons):
            rows.append(
                {
                    "scenario": scenario,
                    "horizon_years": horizon,
                    "repriced_share": repriced[index],
                    "bias_pp": (repriced[index] - benchmark[index]) * 100.0,
                    "incremental_burden_pct_gdp": repriced[index]
                    * debt_pct_gdp
                    * shock_rate,
                }
            )
    return pd.DataFrame(rows)


def kernel_bootstrap_band(
    inputs: KernelInputs,
    behavioural_draws: pd.Series,
    *,
    shock_bps: float = 100.0,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> pd.DataFrame:
    """Propagate bootstrap behavioural draws through the repricing kernel."""
    draws = behavioural_draws.dropna().astype(float)
    if draws.empty:
        raise ValidationError("kernel bootstrap band requires behavioural draws")

    rows: list[dict[str, object]] = []
    for horizon in horizons:
        values = [
            float(
                build_kernel(
                    inputs,
                    shock_bps=shock_bps,
                    behavioural_response=response,
                    horizons=(horizon,),
                )["repriced_share"].iloc[0]
            )
            for response in draws
        ]
        series = pd.Series(values)
        rows.append(
            {
                "horizon_years": horizon,
                "repriced_share_p05": series.quantile(0.05),
                "repriced_share_p25": series.quantile(0.25),
                "repriced_share_p50": series.quantile(0.50),
                "repriced_share_p75": series.quantile(0.75),
                "repriced_share_p95": series.quantile(0.95),
            }
        )
    return pd.DataFrame(rows)


def scenario_fan_chart(
    inputs: KernelInputs,
    behavioural_draws: pd.Series,
    *,
    debt_pct_gdp: float,
    nominal_gdp_mio_eur: float,
    initial_rate_pct: float,
    draws: int = 2_000,
    horizon_years: int = HORIZON_YEARS,
) -> pd.DataFrame:
    """Monte Carlo fan chart for rate-shock pass-through and GDP dilution."""
    behaviour = behavioural_draws.dropna().astype(float).to_numpy()
    if len(behaviour) == 0:
        raise ValidationError("scenario fan chart requires behavioural draws")

    generator = np.random.default_rng(MONTE_CARLO_SEED)
    shock_draws = np.clip(generator.normal(loc=100.0, scale=50.0, size=draws), 0.0, 250.0)
    growth_draws = np.clip(generator.normal(loc=0.04, scale=0.015, size=draws), -0.01, 0.08)
    behaviour_draws = generator.choice(behaviour, size=draws, replace=True)

    rows: list[dict[str, object]] = []
    horizons = tuple(range(1, horizon_years + 1))
    for draw, (shock, growth, response) in enumerate(
        zip(shock_draws, growth_draws, behaviour_draws, strict=True)
    ):
        kernel = build_kernel(
            inputs,
            shock_bps=float(shock),
            behavioural_response=float(response),
            horizons=horizons,
        )
        repriced = kernel["repriced_share"].to_numpy()
        shock_pct = shock / 100.0
        years = np.asarray(horizons, dtype=float)
        gdp = nominal_gdp_mio_eur * (1.0 + growth) ** years
        debt_ratio = debt_pct_gdp * (nominal_gdp_mio_eur / gdp)
        rate = initial_rate_pct + repriced * shock_pct
        baseline_rate = np.full_like(rate, initial_rate_pct)
        burden = rate * debt_ratio / 100.0
        baseline_burden = baseline_rate * debt_ratio / 100.0
        incremental_burden = burden - baseline_burden

        for index, horizon in enumerate(horizons):
            rows.append(
                {
                    "draw": draw,
                    "horizon_years": horizon,
                    "shock_bps": shock,
                    "nominal_growth": growth,
                    "behavioural_response": response,
                    "incremental_burden_pct_gdp": incremental_burden[index],
                }
            )

    frame = pd.DataFrame(rows)
    quantiles = (
        frame.groupby("horizon_years")["incremental_burden_pct_gdp"]
        .quantile(np.asarray([0.05, 0.25, 0.50, 0.75, 0.95], dtype=float))
        .unstack()
        .rename(
            columns={
                0.05: "burden_p05",
                0.25: "burden_p25",
                0.50: "burden_p50",
                0.75: "burden_p75",
                0.95: "burden_p95",
            }
        )
        .reset_index()
    )
    quantiles["mean_shock_bps"] = float(shock_draws.mean())
    quantiles["mean_nominal_growth_pct"] = float(growth_draws.mean() * 100.0)
    quantiles["draws"] = draws
    return quantiles
