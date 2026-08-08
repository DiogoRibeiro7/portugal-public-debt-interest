"""Generate every number the repricing manuscript quotes.

No value is typed into the LaTeX source. The manuscript reads macros emitted
here from the processed artefacts, and ``verify_manuscript_values`` fails the
build if a hand-typed number appears where a macro should be.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import matplotlib
import pandas as pd

from pt_debt.repricing.estimate import OUTCOME, REGRESSORS, monthly_retail_series
from pt_debt.repricing.kernel import (
    REFIXING_PROFILE_PATH,
    KernelInputs,
    bias_table,
    fiscal_translation,
    refixing_comparison,
)
from pt_debt.repricing.simulate import (
    kernel_bootstrap_band,
    model_comparison,
    scenario_fan_chart,
    sensitivity_grid,
)
from pt_debt_interest.exceptions import ValidationError

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

matplotlib.rcParams["svg.hashsalt"] = "pt-debt-repricing"

#: LaTeX control sequences cannot contain digits, so horizons and cut years
#: are spelled out in macro names.
WORDS: Final[dict[int, str]] = {
    1: "One", 3: "Three", 5: "Five", 10: "Ten",
    2014: "Fourteen", 2018: "Eighteen", 2021: "TwentyOne",
}

MACRO_FILENAME: Final[str] = "generated_values.tex"
TABLE_DIRNAME: Final[str] = "tables"
FIGURE_DIRNAME: Final[str] = "figures"
LATEX_BUILTINS: Final[frozenset[str]] = frozenset({"Delta"})


def _macro(name: str, value: object) -> str:
    return rf"\newcommand{{\{name}}}{{{value}}}"


def _fmt(value: object, digits: int = 2) -> str:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    return f"{number:.{digits}f}"


def _as_float(value: object) -> float:
    return float(str(value))


def _as_int(value: object) -> int:
    return int(_as_float(value))


def _kernel_inputs_from_panel(
    panel: pd.DataFrame, as_of: pd.Timestamp | None = None
) -> KernelInputs:
    """Portfolio state at ``as_of``, defaulting to the end of the panel.

    A backtest must reconstruct the state as it stood at its cut date. Passing
    the latest observation into a prediction that starts years earlier is
    look-ahead, so ``as_of`` is not optional at those call sites.
    """
    window = panel if as_of is None else panel.loc[panel["period"].le(as_of)]
    if window.empty:
        raise ValidationError(f"panel has no observations at or before {as_of}")
    latest = window.loc[window["period"].eq(window["period"].max())]

    def _class_share(name: str) -> float:
        rows = latest.loc[latest["instrument_class"].eq(name), "share_of_total_debt"]
        return float(rows.iloc[0]) if not rows.empty else 0.0

    # Savings Certificates are variable-rate (Series F tracks three-month
    # Euribor); Treasury Certificates carry a guaranteed fixed schedule. The
    # kernel needs them apart to build a partition that does not overlap.
    return KernelInputs(
        average_residual_maturity_years=float(
            latest["average_residual_term_years"].iloc[0]
        ),
        fixed_rate_share=float(latest["share_fixed_rate_pct"].iloc[0]) / 100.0,
        retail_share_of_stock=float(latest["share_of_total_debt"].sum()),
        retail_variable_share=_class_share("savings_certificates"),
        retail_fixed_share=_class_share("treasury_certificates"),
    )


def _simulation_inputs(paths: pd.DataFrame) -> dict[str, float]:
    """Recover the time-zero state the scenarios started from.

    Read from the **zero-growth** path deliberately. Under zero growth the
    denominator has not moved, so the horizon-one debt ratio and implied GDP
    are still the time-zero values. Taking them from the central-growth path
    instead returned a denominator that had already been grown one year, and
    the fan chart then grew it again from there.
    """
    row = paths.loc[
        paths["growth_path"].eq("zero_growth")
        & paths["shock_bps"].eq(100)
        & paths["horizon_years"].eq(1)
    ].iloc[0]
    burden = float(row["incremental_burden_pct_gdp"])
    interest = float(row["incremental_interest_mio_eur"])
    return {
        "initial_rate_pct": float(row["effective_rate_pct"])
        - float(row["repriced_share"]),
        "debt_pct_gdp": float(row["debt_pct_gdp"]),
        "nominal_gdp_mio_eur": interest / (burden / 100.0),
    }


def _behavioural_sensitivity_bounds(replicates: pd.DataFrame) -> tuple[float, float, float]:
    """Central behavioural effect is zero; the fitted response is a sensitivity."""
    widening = replicates["spread_widening_pp"].dropna().astype(float)
    return (
        0.0,
        min(0.0, float(widening.quantile(0.025))),
        max(0.0, float(widening.quantile(0.975))),
    )


def _bias_frame(inputs: KernelInputs, replicates: pd.DataFrame) -> pd.DataFrame:
    central, low, high = _behavioural_sensitivity_bounds(replicates)
    return bias_table(
        inputs,
        shock_bps=100,
        behavioural_response=central,
        behavioural_low=low,
        behavioural_high=high,
    )


def _fiscal_bias_frame(
    bias: pd.DataFrame,
    fiscal_reference: pd.DataFrame,
) -> pd.DataFrame:
    one_year = fiscal_reference.loc[fiscal_reference["horizon_years"].eq(1)].iloc[0]
    old_bias = float(one_year["total_bias_pp"])
    old_interest = float(one_year["bias_interest_mio_eur"])
    old_pct_gdp = float(one_year["bias_interest_pct_gdp"])
    debt_pct_gdp = old_pct_gdp / (old_bias / 100.0 * 100 / 10_000.0)
    nominal_gdp_mio_eur = old_interest / (old_pct_gdp / 100.0)
    return fiscal_translation(
        bias,
        debt_pct_gdp=debt_pct_gdp,
        shock_bps=100,
        nominal_gdp_mio_eur=nominal_gdp_mio_eur,
    )


def _table(
    *,
    caption: str,
    label: str,
    columns: str,
    header: list[str],
    rows: list[list[str]],
    notes: str | None = None,
    resize: bool = False,
) -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
    ]
    if resize:
        lines.append(r"\resizebox{\textwidth}{!}{%")
    lines.extend(
        [
            rf"\begin{{tabular}}{{{columns}}}",
            r"\toprule",
            " & ".join(header) + r" \\",
            r"\midrule",
            *(" & ".join(row) + r" \\" for row in rows),
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    if resize:
        lines.append("}")
    if notes:
        lines.extend([r"\par\smallskip", rf"\parbox{{0.92\textwidth}}{{\small {notes}}}"])
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


MODEL_LABELS: Final[dict[str, str]] = {
    "estimated_kernel": "Scenario kernel",
    "wam_benchmark": "WAM benchmark",
    "immediate_full_pass_through": "Immediate full pass-through",
    "random_walk": "Random walk",
}


def _row(frame: pd.DataFrame, column: str, value: str | int) -> pd.Series:
    match = frame.loc[frame[column].eq(value)]
    if match.empty:
        raise ValidationError(f"no row with {column} == {value!r}")
    return match.iloc[0]


def _refixing_rows(profile: pd.DataFrame, inputs: KernelInputs) -> list[list[str]]:
    comparison = refixing_comparison(profile, inputs)
    rows: list[list[str]] = []
    for row in comparison.itertuples():
        lower = _as_float(row.bracket_lower_years)
        upper = _as_float(row.bracket_upper_years)
        label = f"{_fmt(lower, 0)}-{_fmt(upper, 0)}"
        rows.append(
            [
                label,
                _fmt(100.0 * _as_float(row.published_share), 1),
                _fmt(100.0 * _as_float(row.kernel_implied_share), 1),
                _fmt(row.difference_pp, 1),
            ]
        )
    return rows


def build_macros(processed_dir: Path, panel_path: Path) -> list[str]:
    """Read the artefacts and emit the manuscript's macros."""
    fiscal_reference = pd.read_csv(processed_dir / "kernels" / "kernel_bias_fiscal.csv")
    coefficients = pd.read_csv(processed_dir / "estimates" / "s1_coefficients.csv")
    replicates = pd.read_csv(
        processed_dir / "estimates" / "s1_bootstrap_replicates.csv"
    )
    placebo = pd.read_csv(processed_dir / "estimates" / "s1_placebo.csv")
    backtest = pd.read_csv(processed_dir / "scenarios" / "backtest_summary.csv")
    paths = pd.read_csv(processed_dir / "scenarios" / "pass_through_paths.csv")
    panel = pd.read_csv(panel_path)
    panel["period"] = pd.to_datetime(panel["period"])
    inputs = _kernel_inputs_from_panel(panel)
    sim_inputs = _simulation_inputs(paths)
    bias = _bias_frame(inputs, replicates)
    fiscal = _fiscal_bias_frame(bias, fiscal_reference)

    macros: list[str] = []

    # --- portfolio state
    latest = panel.loc[panel["period"].eq(panel["period"].max())]
    fixed_share = float(latest["share_fixed_rate_pct"].iloc[0])
    macros += [
        _macro("PortfolioAsOf", latest["period"].max().strftime("%B %Y")),
        _macro(
            "AverageResidualMaturity",
            f"{float(latest['average_residual_term_years'].iloc[0]):.2f}",
        ),
        _macro("FixedRateSharePct", f"{fixed_share:.1f}"),
        _macro("FloatingSharePct", f"{100.0 - fixed_share:.1f}"),
        _macro("RetailSharePct", f"{float(latest['share_of_total_debt'].sum()) * 100.0:.1f}"),
    ]

    # --- the retail episode, from the raw panel
    retail = (
        panel.loc[panel["instrument_class"].eq("savings_certificates")]
        .set_index("period")["outstanding_mio_eur"]
        .sort_index()
    )
    start, end = retail.loc["2022-06-30"], retail.loc["2023-05-31"]
    macros += [
        _macro("RetailStockStartBn", f"{start / 1000.0:.1f}"),
        _macro("RetailStockPeakBn", f"{end / 1000.0:.1f}"),
        _macro("RetailGrowthPct", f"{(end / start - 1.0) * 100.0:.0f}"),
        _macro("RetailPeakInflowMio", f"{retail.diff().max():,.0f}"),
    ]

    # --- kernel bias
    for horizon in (1, 3, 5, 10):
        row = _row(bias, "horizon_years", horizon)
        macros += [
            _macro(f"BiasTotalH{WORDS[horizon]}", f"{row['total_bias_pp']:.2f}"),
            _macro(f"BiasShapeH{WORDS[horizon]}", f"{row['shape_bias_pp']:.2f}"),
            _macro(f"BiasBehaviourH{WORDS[horizon]}", f"{row['behaviour_bias_pp']:.2f}"),
            _macro(f"WamShareH{WORDS[horizon]}", f"{row['wam_implied_share']:.4f}"),
            _macro(f"EstimatedShareH{WORDS[horizon]}", f"{row['estimated_share']:.4f}"),
        ]
    fiscal_one = _row(fiscal, "horizon_years", 1)
    macros += [
        _macro("BiasInterestPctGdpHOne", f"{fiscal_one['bias_interest_pct_gdp']:.3f}"),
        _macro("BiasInterestMioHOne", f"{fiscal_one['bias_interest_mio_eur']:,.0f}"),
    ]

    # --- estimation
    widening = _row(coefficients, "term", "spread_widening_pp")
    macros += [
        _macro("SpreadWideningCoef", f"{widening['coefficient']:+.4f}"),
        _macro("SpreadWideningSe", f"{widening['std_error']:.4f}"),
        _macro("SpreadWideningP", f"{widening['p_value']:.2f}"),
        _macro(
            "EstimationObservations",
            # The estimator aggregates to a monthly series, so the stacked
            # class-month count would overstate the sample by a factor of
            # roughly the number of classes.
            f"{len(monthly_retail_series(panel).dropna(subset=[OUTCOME, *REGRESSORS])):,}",
        ),
    ]
    difference = replicates["spread_widening_pp"] - replicates["spread_narrowing_pp"]
    macros += [
        _macro("AsymmetryPoint", f"{difference.mean():+.3f}"),
        _macro("AsymmetryLow", f"{difference.quantile(0.025):+.3f}"),
        _macro("AsymmetryHigh", f"{difference.quantile(0.975):+.3f}"),
        _macro("BootstrapReplicates", f"{len(difference):,}"),
    ]
    placebo_row = _row(placebo, "term", "share_fixed_rate_pct")
    macros += [
        _macro("PlaceboCoef", f"{placebo_row['coefficient']:+.5f}"),
        _macro("PlaceboP", f"{placebo_row['p_value']:.2f}"),
    ]

    # --- backtest
    for cut in (2014, 2018, 2021):
        window = backtest.loc[backtest["cut_year"].eq(cut)]
        for model, label in (
            ("estimated_kernel", "Est"),
            ("wam_benchmark", "Wam"),
        ):
            value = _row(window, "model", model)["mean_abs_error_bps"]
            macros.append(_macro(f"Backtest{label}{WORDS[cut]}", f"{value:.2f}"))

    # --- growth-path correction
    at_five = paths.loc[paths["shock_bps"].eq(100) & paths["horizon_years"].eq(5)]
    zero = _row(at_five, "growth_path", "zero_growth")["incremental_burden_pct_gdp"]
    central = _row(at_five, "growth_path", "central")["incremental_burden_pct_gdp"]
    macros += [
        _macro("ShockBurdenZeroGrowth", f"{zero:.3f}"),
        _macro("ShockBurdenCentralGrowth", f"{central:.3f}"),
        _macro("GrowthCorrectionPct", f"{(1.0 - central / zero) * 100.0:.0f}"),
    ]

    fan = scenario_fan_chart(
        inputs,
        replicates["spread_widening_pp"],
        debt_pct_gdp=sim_inputs["debt_pct_gdp"],
        nominal_gdp_mio_eur=sim_inputs["nominal_gdp_mio_eur"],
        initial_rate_pct=sim_inputs["initial_rate_pct"],
    )
    fan_five = _row(fan, "horizon_years", 5)
    macros += [
        _macro("FanDraws", f"{_as_int(fan_five['draws']):,}"),
        _macro("FanMeanShockBps", f"{fan_five['mean_shock_bps']:.0f}"),
        _macro("FanMeanGrowthPct", f"{fan_five['mean_nominal_growth_pct']:.1f}"),
        _macro("FanBurdenLowHFive", f"{fan_five['burden_p05']:.3f}"),
        _macro("FanBurdenMedianHFive", f"{fan_five['burden_p50']:.3f}"),
        _macro("FanBurdenHighHFive", f"{fan_five['burden_p95']:.3f}"),
    ]

    _, behavioural_low, behavioural_high = _behavioural_sensitivity_bounds(replicates)
    sensitivity = sensitivity_grid(
        inputs,
        behavioural_response=0.0,
        behavioural_low=behavioural_low,
        behavioural_high=behavioural_high,
        debt_pct_gdp=sim_inputs["debt_pct_gdp"],
    )
    one_year = sensitivity.loc[sensitivity["horizon_years"].eq(1), "bias_pp"]
    macros.append(
        _macro("SensitivityRangeHOne", f"{one_year.max() - one_year.min():.2f}")
    )
    return macros


def write_macros(processed_dir: Path, panel_path: Path, output_dir: Path) -> Path:
    """Write the generated macros beside the manuscript."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MACRO_FILENAME
    path.write_text("\n".join(build_macros(processed_dir, panel_path)) + "\n", encoding="utf-8")
    return path


def write_tables(processed_dir: Path, panel_path: Path, output_dir: Path) -> list[Path]:
    """Write LaTeX tables used by the repricing manuscript."""
    table_dir = output_dir / TABLE_DIRNAME
    table_dir.mkdir(parents=True, exist_ok=True)
    coefficients = pd.read_csv(processed_dir / "estimates" / "s1_coefficients.csv")
    replicates = pd.read_csv(processed_dir / "estimates" / "s1_bootstrap_replicates.csv")
    backtest = pd.read_csv(processed_dir / "scenarios" / "backtest_summary.csv")
    half_life_frame = pd.read_csv(processed_dir / "scenarios" / "half_life.csv")
    scenario_paths = pd.read_csv(processed_dir / "scenarios" / "pass_through_paths.csv")
    panel = pd.read_csv(panel_path)
    panel["period"] = pd.to_datetime(panel["period"])
    latest = panel.loc[panel["period"].eq(panel["period"].max())]
    inputs = _kernel_inputs_from_panel(panel)
    sim_inputs = _simulation_inputs(scenario_paths)
    bias = _bias_frame(inputs, replicates)

    paths: list[Path] = []
    portfolio_rows = [
        ["Observation month", latest["period"].max().strftime("%B %Y")],
        [
            "Average residual maturity (years)",
            _fmt(latest["average_residual_term_years"].iloc[0], 2),
        ],
        [
            "Fixed-rate share (\\%)",
            _fmt(latest["share_fixed_rate_pct"].iloc[0], 1),
        ],
        [
            "Floating or indexed share (\\%)",
            _fmt(100.0 - float(latest["share_fixed_rate_pct"].iloc[0]), 1),
        ],
        [
            "Retail certificate share (\\%)",
            _fmt(float(latest["share_of_total_debt"].sum()) * 100.0, 1),
        ],
        ["Panel start", panel["period"].min().strftime("%B %Y")],
        ["Panel end", panel["period"].max().strftime("%B %Y")],
    ]
    path = table_dir / "portfolio_inputs.tex"
    path.write_text(
        _table(
            caption="Portfolio inputs for the repricing kernel",
            label="tab:repricing-portfolio",
            columns="lr",
            header=["Quantity", "Value"],
            rows=portfolio_rows,
            notes=(
                "Source: author calculations from IGCP monthly stocks and "
                "portfolio indicators."
            ),
        ),
        encoding="utf-8",
    )
    paths.append(path)

    coefficient_rows = [
        [
            str(row.term).replace("_", r"\_"),
            _fmt(row.coefficient, 4),
            _fmt(row.std_error, 4),
            _fmt(row.p_value, 2),
        ]
        for row in coefficients.itertuples()
    ]
    path = table_dir / "estimation_coefficients.tex"
    path.write_text(
        _table(
            caption="Subscription-margin regression",
            label="tab:repricing-estimation",
            columns="lrrr",
            header=["Term", "Coefficient", "Newey--West s.e.", "$p$-value"],
            rows=coefficient_rows,
            notes=(
                "Outcome: positive outstanding-value change as a share of "
                "opening class stock. Source: author calculations from IGCP "
                "and ECB data."
            ),
        ),
        encoding="utf-8",
    )
    paths.append(path)

    bias_rows = [
        [
            f"{_as_int(row.horizon_years)}",
            _fmt(100.0 * _as_float(row.wam_implied_share), 2),
            _fmt(100.0 * _as_float(row.estimated_share), 2),
            _fmt(row.total_bias_pp, 2),
            _fmt(row.shape_bias_pp, 2),
            _fmt(row.behaviour_bias_pp, 2),
        ]
        for row in bias.itertuples()
    ]
    path = table_dir / "kernel_bias.tex"
    path.write_text(
        _table(
            caption="Scenario-minus-WAM repricing differences, +100 bps",
            label="tab:bias",
            columns="rrrrrr",
            header=[
                "Horizon",
                "Proxy share (\\%)",
                "Scenario share (\\%)",
                "Difference (pp)",
                "Shape (pp)",
                "Behaviour (pp)",
            ],
            rows=bias_rows,
            notes="Source: author calculations. Shape and behaviour sum to the total.",
            resize=True,
        ),
        encoding="utf-8",
    )
    paths.append(path)

    refixing_path = Path(REFIXING_PROFILE_PATH)
    if refixing_path.is_file():
        profile = pd.read_csv(refixing_path)
        reference = str(profile["reference_date"].iloc[0])
        path = table_dir / "refixing_comparison.tex"
        path.write_text(
            _table(
                caption="Official ESDM refixing benchmark and scenario kernel",
                label="tab:refixing-comparison",
                columns="lrrr",
                header=[
                    "Window, years",
                    "ESDM share (\\%)",
                    "Scenario share (\\%)",
                    "Difference (pp)",
                ],
                rows=_refixing_rows(profile, inputs),
                notes=(
                    "Official shares are Portugal's ESDM refixing-risk "
                    f"windows at {reference}, as published by IGCP. The "
                    "comparison uses the same cumulative windows."
                ),
            ),
            encoding="utf-8",
        )
        paths.append(path)

    _, behavioural_low, behavioural_high = _behavioural_sensitivity_bounds(replicates)
    sensitivity = sensitivity_grid(
        inputs,
        behavioural_response=0.0,
        behavioural_low=behavioural_low,
        behavioural_high=behavioural_high,
        debt_pct_gdp=sim_inputs["debt_pct_gdp"],
    )
    labels = {
        "central": "Central kernel",
        "slow_reset": "Slow reset (two-year cycle)",
        "fast_reset": "Fast reset (six-month cycle)",
        "partial_reset_loading": "Reset loading 0.5",
        "weak_reset_loading": "Reset loading 0.25",
        "memoryless_contractual_shape": "Memoryless contractual shape",
        "behaviour_off": "Behaviour off",
        "behaviour_lower_bound": "Behaviour low case",
        "behaviour_upper_bound": "Behaviour high case",
    }
    sensitivity_rows = []
    for scenario, group in sensitivity.groupby("scenario", sort=False):
        ordered = group.set_index("horizon_years")
        sensitivity_rows.append(
            [
                labels[str(scenario)],
                _fmt(ordered.loc[1, "bias_pp"], 2),
                _fmt(100.0 * _as_float(ordered.loc[5, "repriced_share"]), 2),
                _fmt(ordered.loc[5, "incremental_burden_pct_gdp"], 3),
            ]
        )
    path = table_dir / "sensitivity_checks.tex"
    path.write_text(
        _table(
            caption="Sensitivity of the kernel to modelling assumptions, +100 bps",
            label="tab:sensitivity",
            columns="lrrr",
            header=[
                "Scenario",
                "One-year bias (pp)",
                "Five-year repriced share (\\%)",
                "Five-year burden (\\% GDP)",
            ],
            rows=sensitivity_rows,
            notes=(
                "The table varies one assumption at a time around the central "
                "kernel. Source: author simulations."
            ),
            resize=True,
        ),
        encoding="utf-8",
    )
    paths.append(path)

    half_life_rows = [
        [
            f"{_as_int(row.shock_bps)}",
            _fmt(row.asymptote_pct_gdp, 3),
            _fmt(row.half_life_years, 1),
        ]
        for row in half_life_frame.sort_values("shock_bps").itertuples()
    ]
    path = table_dir / "half_life.tex"
    path.write_text(
        _table(
            caption="Half-life of incremental pass-through under central nominal growth",
            label="tab:repricing-half-life",
            columns="rrr",
            header=["Shock (bps)", "Maximum burden effect (\\% GDP)", "Half-life (years)"],
            rows=half_life_rows,
            notes=(
                "The half-life is the first horizon at which the absolute "
                "burden effect reaches half of its simulated maximum."
            ),
        ),
        encoding="utf-8",
    )
    paths.append(path)

    comparison = model_comparison(backtest)
    comparison_rows = [
        [
            MODEL_LABELS.get(str(row.model), str(row.model).replace("_", r"\_")),
            _fmt(row.mean_abs_error_bps, 2),
            _fmt(row.worst_bps, 2),
            f"{_as_int(row.win_count)}",
            f"{_as_int(row.cut_years)}",
        ]
        for row in comparison.itertuples()
    ]
    path = table_dir / "model_comparison.tex"
    path.write_text(
        _table(
            caption="Model comparison across validation cut years",
            label="tab:model-comparison",
            columns="lrrrr",
            header=[
                "Model",
                "Mean abs. error (bps)",
                "Worst error (bps)",
                "Wins",
                "Cuts",
            ],
            rows=comparison_rows,
            notes=(
                "Wins count cut years in which the model has the lowest mean "
                "absolute error. Source: author calculations."
            ),
            resize=True,
        ),
        encoding="utf-8",
    )
    paths.append(path)

    backtest_rows = [
        [
            str(_as_int(row.cut_year)),
            MODEL_LABELS.get(str(row.model), str(row.model).replace("_", r"\_")),
            _fmt(row.mean_abs_error_bps, 2),
            _fmt(row.worst_bps, 2),
            str(_as_int(row.n)),
        ]
        for row in backtest.sort_values(["cut_year", "mean_abs_error_bps"]).itertuples()
    ]
    path = table_dir / "backtest_summary.tex"
    path.write_text(
        _table(
            caption="Conditional historical validation errors",
            label="tab:backtest",
            columns="rlrrr",
            header=["Cut year", "Model", "Mean abs. error (bps)", "Worst error (bps)", "$N$"],
            rows=backtest_rows,
            notes=(
                "Errors are basis points on the realised average debt rate. "
                "Source: author calculations."
            ),
            resize=True,
        ),
        encoding="utf-8",
    )
    paths.append(path)
    return paths


def _save_pdf(fig: Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", metadata={"CreationDate": None})
    plt.close(fig)
    return path


def write_figures(processed_dir: Path, panel_path: Path, output_dir: Path) -> list[Path]:
    """Write PDF figures used by the repricing manuscript."""
    figure_dir = output_dir / FIGURE_DIRNAME
    figure_dir.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(panel_path)
    panel["period"] = pd.to_datetime(panel["period"])
    paths = pd.read_csv(processed_dir / "scenarios" / "pass_through_paths.csv")
    replicates = pd.read_csv(processed_dir / "estimates" / "s1_bootstrap_replicates.csv")
    inputs = _kernel_inputs_from_panel(panel)
    sim_inputs = _simulation_inputs(paths)
    bias = _bias_frame(inputs, replicates)

    written: list[Path] = []

    retail = panel.loc[panel["instrument_class"].eq("savings_certificates")].copy()
    recent = retail.loc[retail["period"].ge(pd.Timestamp("2019-01-31"))]
    fig, ax_stock = plt.subplots(figsize=(8.0, 4.6))
    ax_stock.plot(recent["period"], recent["outstanding_mio_eur"] / 1000.0, color="#1f77b4")
    ax_stock.set_ylabel("Savings certificates, EUR bn")
    ax_stock.grid(True, alpha=0.25)
    ax_spread = ax_stock.twinx()
    ax_spread.plot(
        recent["period"],
        recent["competing_return_spread_pp"],
        color="#b91c1c",
        linestyle="--",
    )
    ax_spread.set_ylabel("Competing-return spread, pp")
    ax_stock.set_xlabel("")
    written.append(_save_pdf(fig, figure_dir / "retail_stock_and_spread.pdf"))

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    x = bias["horizon_years"].astype(float)
    ax.plot(x, 100.0 * bias["wam_implied_share"], marker="o", label="WAM proxy")
    ax.plot(x, 100.0 * bias["estimated_share"], marker="o", label="Scenario kernel")
    ax.fill_between(
        x,
        100.0 * bias["estimated_share_low"],
        100.0 * bias["estimated_share_high"],
        color="#2563eb",
        alpha=0.16,
        label="Estimated interval",
    )
    ax.set_xlabel("Horizon, years")
    ax.set_ylabel("Share repriced, percent")
    ax.grid(True, alpha=0.25)
    ax.legend()
    written.append(_save_pdf(fig, figure_dir / "kernel_comparison.pdf"))

    band = kernel_bootstrap_band(inputs, replicates["spread_widening_pp"])
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    x_band = band["horizon_years"].astype(float).to_numpy()
    ax.fill_between(
        x_band,
        100.0 * band["repriced_share_p05"].to_numpy(),
        100.0 * band["repriced_share_p95"].to_numpy(),
        color="#4f46e5",
        alpha=0.16,
        label="5--95 percentile",
    )
    ax.fill_between(
        x_band,
        100.0 * band["repriced_share_p25"].to_numpy(),
        100.0 * band["repriced_share_p75"].to_numpy(),
        color="#4f46e5",
        alpha=0.28,
        label="25--75 percentile",
    )
    ax.plot(
        x_band,
        100.0 * band["repriced_share_p50"].to_numpy(),
        color="#312e81",
        marker="o",
        label="Bootstrap median",
    )
    ax.plot(
        x_band,
        100.0 * bias["wam_implied_share"].to_numpy(),
        color="#111827",
        label="WAM",
    )
    ax.set_xlabel("Horizon, years")
    ax.set_ylabel("Share repriced, percent")
    ax.grid(True, alpha=0.25)
    ax.legend()
    written.append(_save_pdf(fig, figure_dir / "kernel_bootstrap_band.pdf"))

    subset = paths.loc[paths["shock_bps"].eq(100)].copy()
    labels = {
        "zero_growth": "Zero nominal growth",
        "low": "Low nominal growth",
        "central": "Central nominal growth",
    }
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for name, group in subset.groupby("growth_path"):
        ordered = group.sort_values("horizon_years")
        ax.plot(
            ordered["horizon_years"],
            ordered["incremental_burden_pct_gdp"],
            marker="o",
            label=labels.get(str(name), str(name)),
        )
    ax.set_xlabel("Horizon, years")
    ax.set_ylabel("Incremental burden, percent of GDP")
    ax.grid(True, alpha=0.25)
    ax.legend()
    written.append(_save_pdf(fig, figure_dir / "pass_through_growth_paths.pdf"))

    fan = scenario_fan_chart(
        inputs,
        replicates["spread_widening_pp"],
        debt_pct_gdp=sim_inputs["debt_pct_gdp"],
        nominal_gdp_mio_eur=sim_inputs["nominal_gdp_mio_eur"],
        initial_rate_pct=sim_inputs["initial_rate_pct"],
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    x_fan = fan["horizon_years"].astype(float).to_numpy()
    ax.fill_between(
        x_fan,
        fan["burden_p05"].to_numpy(),
        fan["burden_p95"].to_numpy(),
        color="#0f766e",
        alpha=0.16,
        label="5--95 percentile",
    )
    ax.fill_between(
        x_fan,
        fan["burden_p25"].to_numpy(),
        fan["burden_p75"].to_numpy(),
        color="#0f766e",
        alpha=0.28,
        label="25--75 percentile",
    )
    ax.plot(
        x_fan,
        fan["burden_p50"].to_numpy(),
        color="#134e4a",
        marker="o",
        label="Median",
    )
    ax.set_xlabel("Horizon, years")
    ax.set_ylabel("Incremental burden, percent of GDP")
    ax.grid(True, alpha=0.25)
    ax.legend()
    written.append(_save_pdf(fig, figure_dir / "scenario_fan_chart.pdf"))
    return written


def verify_manuscript_values(tex_path: Path) -> list[str]:
    """Return hand-typed numbers found in the manuscript body.

    Every quantity must arrive through a macro. Structural numbers -- font
    sizes, figure widths, years in prose -- are excluded, so what remains is a
    result typed by hand.
    """
    if not tex_path.is_file():
        raise ValidationError(f"manuscript not found: {tex_path}")
    source = tex_path.read_text(encoding="utf-8")
    body = source.split(r"\begin{document}")[-1].split(r"\begin{thebibliography}")[0]
    body = re.sub(r"\\includegraphics\[[^\]]*\]\{[^}]*\}", " ", body)
    body = re.sub(r"\\(?:label|ref|cite|input)\{[^}]*\}", " ", body)
    # Identifiers, not results: a DOI or URL is full of digits and dots.
    body = re.sub(r"\\(?:doi|url|texttt)\{[^}]*\}", " ", body)
    body = re.sub(r"%[^\n]*", " ", body)
    # Four-digit years are prose, not results.
    body = re.sub(r"(?<!\d)(19|20)\d{2}(?!\d)", " ", body)
    return re.findall(r"(?<![\w.])-?\d+\.\d+", body)


def undefined_macros(tex_path: Path, macro_path: Path) -> list[str]:
    """Return generated-style macros the manuscript calls but nothing defines.

    A macro that vanishes from the artefacts -- a horizon dropped, a cut date
    renamed -- would otherwise surface as a LaTeX error at compile time, or
    worse, as a silently empty number.
    """
    defined = set(
        re.findall(r"\\newcommand\{\\(\w+)\}", macro_path.read_text(encoding="utf-8"))
    )
    body = tex_path.read_text(encoding="utf-8").split(r"\begin{document}")[-1]
    used = set(re.findall(r"\\([A-Z]\w+)", body))
    return sorted(
        name for name in used - defined if not name.isupper() and name not in LATEX_BUILTINS
    )
