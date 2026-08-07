"""``pt-debt repricing`` command group.

Registered onto the existing CLI rather than forking it: one entry point, one
dependency set, two papers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import typer
import yaml

from pt_debt_interest.exceptions import SourceError

from . import estimate, kernel, manuscript, simulate
from . import panel as panel_module
from .acquire import ecb, igcp

app = typer.Typer(help="Repricing-kernel research commands.")

DEFAULT_CONFIG = Path("config/repricing.yaml")
DEFAULT_BURDEN_DATASET = Path("data/processed/portugal_debt_interest.csv")


def load_config(path: Path) -> dict[str, Any]:
    """Read the repricing configuration."""
    if not path.is_file():
        raise typer.BadParameter(f"repricing configuration not found: {path}")
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle) or {}
    return loaded


@app.command("acquire")
def acquire_command(
    config: Path = DEFAULT_CONFIG,
    refresh: bool = typer.Option(
        False, help="Re-fetch from source instead of reusing the newest cached payload."
    ),
) -> None:
    """Acquire instrument-level and covariate inputs for the repricing work."""
    settings = load_config(config)
    raw_dir = Path(settings["paths"]["raw"])
    http = settings.get("http", {})
    timeout = float(http.get("timeout_seconds", 90))

    failures: list[str] = []

    try:
        stock = igcp.fetch_debt_stock(
            settings["igcp"]["debt_stock_monthly_url"],
            raw_dir,
            refresh=refresh,
            timeout_seconds=timeout,
        )
        typer.echo(
            f"igcp debt stock: {stock.fetch.path} "
            f"({stock.frame['series'].nunique()} series, {len(stock.frame)} rows)"
        )
    except SourceError as exc:
        failures.append(f"igcp debt stock: {exc}")

    try:
        indicators = igcp.fetch_debt_indicators(
            settings["igcp"]["debt_indicators_url"],
            raw_dir,
            refresh=refresh,
            timeout_seconds=timeout,
        )
        typer.echo(
            f"igcp debt indicators: {indicators.fetch.path} "
            f"({indicators.frame['series'].nunique()} series, "
            f"{len(indicators.frame)} rows)"
        )
    except SourceError as exc:
        failures.append(f"igcp debt indicators: {exc}")

    try:
        fetched = ecb.fetch_configured(
            settings["ecb"]["series"],
            raw_dir,
            refresh=refresh,
            timeout_seconds=timeout,
        )
        for name, series in fetched.items():
            typer.echo(f"ecb {name}: {len(series.frame)} observations")
    except SourceError as exc:
        failures.append(str(exc))

    if failures:
        typer.echo("")
        typer.echo("Acquisition incomplete. See docs/manual_ingest.md.")
        for failure in failures:
            typer.echo(f"  - {failure}")
        raise typer.Exit(code=1)


def _monthly(series_frame: pd.DataFrame) -> pd.Series:
    """Align an ECB series to month-end periods.

    Some series are published daily, so collapsing to month end yields many
    observations per month. The month's last observation is taken, which is the
    rate in force at the period boundary the panel is indexed on.
    """
    frame = series_frame.copy()
    frame["period"] = pd.PeriodIndex(frame["period"], freq="M").to_timestamp("M")
    collapsed = frame.groupby("period")["value"].last().sort_index()
    if collapsed.index.has_duplicates:  # pragma: no cover - defensive
        raise ValueError("monthly alignment left duplicate periods")
    return collapsed


@app.command("build-panel")
def build_panel_command(
    config: Path = DEFAULT_CONFIG,
    burden_dataset: Path = DEFAULT_BURDEN_DATASET,
) -> None:
    """Build the monthly repricing panel and its validation report."""
    settings = load_config(config)
    raw_dir = Path(settings["paths"]["raw"])
    processed_dir = Path(settings["paths"]["processed"])
    reports_dir = Path(settings["paths"]["reports"])

    stock = igcp.fetch_debt_stock(settings["igcp"]["debt_stock_monthly_url"], raw_dir)
    indicators = igcp.fetch_debt_indicators(settings["igcp"]["debt_indicators_url"], raw_dir)
    series = settings["ecb"]["series"]
    covariates = {
        name: _monthly(
            ecb.fetch_series(name, series[name]["dataflow"], series[name]["key"], raw_dir).frame
        )
        for name in (
            "policy_rate_deposit_facility",
            "household_deposit_rate_pt_new_business",
        )
    }

    built = panel_module.build_repricing_panel(stock.frame, indicators.frame, covariates)
    built = panel_module.add_competing_return_spread(
        built,
        "policy_rate_deposit_facility",
        "household_deposit_rate_pt_new_business",
    )
    outputs = panel_module.write_panel(built, processed_dir)
    for path in outputs.values():
        typer.echo(path)

    checks = panel_module.validate_panel(built)
    reconciliation = None
    if burden_dataset.is_file():
        reconciliation = panel_module.reconcile_to_aggregate_debt(
            built, pd.read_csv(burden_dataset)
        )

    reports_dir.mkdir(parents=True, exist_ok=True)
    report = reports_dir / "riskset_validation.md"
    lines = [
        "# Repricing panel validation",
        "",
        f"Rows: {len(built)}. Instrument classes: {built['instrument_class'].nunique()}.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Severity | Detail |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {row.check} | {row.passed} | {row.severity} | {row.detail} |"
        for row in checks.itertuples()
    ]
    if reconciliation is not None:
        lines += [
            "",
            "## Reconciliation to the burden paper's debt stock",
            "",
            "IGCP State direct debt and Maastricht general-government debt are "
            "different concepts, so a gap is expected. It is reported per year "
            "rather than asserted away.",
            "",
            "| Year | IGCP (EUR m) | Maastricht (EUR m) | Difference | % of Maastricht |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines += [
            f"| {int(float(str(row.year)))} | {row.igcp_state_direct_debt_mio_eur:,.0f} | "
            f"{row.maastricht_debt_mio_eur:,.0f} | "
            f"{row.difference_mio_eur:,.0f} | "
            f"{row.difference_pct_of_maastricht:.1f}% |"
            for row in reconciliation.itertuples()
        ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo(report)

    failed = checks.loc[~checks["passed"] & checks["severity"].eq("error")]
    if not failed.empty:
        typer.echo("error-severity checks failed:")
        for row in failed.itertuples():
            typer.echo(f"  - {row.check}: {row.detail}")
        raise typer.Exit(code=1)


@app.command("paper")
def paper_command(
    config: Path = DEFAULT_CONFIG,
    paper_dir: Path = Path("paper/repricing"),
) -> None:
    """Regenerate the manuscript's macros and check for hand-typed numbers.

    The manuscript quotes no literal results: every figure arrives through a
    macro generated here from the processed artefacts. A number typed into the
    body would drift silently when the pipeline is rerun, so this command fails
    the build if it finds one.
    """
    settings = load_config(config)
    processed = Path(settings["paths"]["processed"])
    macro_path = manuscript.write_macros(
        processed, processed / "repricing_panel.csv", paper_dir
    )
    typer.echo(macro_path)
    for path in manuscript.write_tables(
        processed, processed / "repricing_panel.csv", paper_dir
    ):
        typer.echo(path)
    for path in manuscript.write_figures(
        processed, processed / "repricing_panel.csv", paper_dir
    ):
        typer.echo(path)

    tex_path = paper_dir / "repricing_kernel.tex"
    missing = manuscript.undefined_macros(tex_path, macro_path)
    if missing:
        typer.echo(f"{tex_path}: macros used but not generated: {', '.join(missing)}")
        raise typer.Exit(code=1)

    literals = manuscript.verify_manuscript_values(tex_path)
    if literals:
        typer.echo(
            f"{tex_path}: {len(literals)} hand-typed number(s) in the body; "
            "every quantity must come from a generated macro:"
        )
        for literal in sorted(set(literals)):
            typer.echo(f"  - {literal}")
        raise typer.Exit(code=1)
    typer.echo(f"{tex_path}: no hand-typed results")


@app.command("all")
def all_command(
    config: Path = DEFAULT_CONFIG,
    burden_dataset: Path = DEFAULT_BURDEN_DATASET,
    paper_dir: Path = Path("paper/repricing"),
) -> None:
    """Run the whole repricing study: panel, estimates, kernels, scenarios, paper.

    Every artefact the manuscript reads was previously produced by ad-hoc
    scripts that were never committed, so a clean clone could build the paper
    only from artefacts that happened to be in the tree. This is the executable
    path from panel to manuscript.
    """
    settings = load_config(config)
    processed = Path(settings["paths"]["processed"])
    panel_path = processed / "repricing_panel.csv"
    if not panel_path.is_file():
        raise typer.BadParameter(
            f"{panel_path} is absent; run `pt-debt repricing build-panel` first"
        )
    if not burden_dataset.is_file():
        raise typer.BadParameter(
            f"{burden_dataset} is absent; run `pt-debt all` for the burden paper first"
        )

    frame = pd.read_csv(panel_path)
    frame["period"] = pd.to_datetime(frame["period"])
    burden = pd.read_csv(burden_dataset)

    # --- estimation
    estimates = processed / "estimates"
    estimates.mkdir(parents=True, exist_ok=True)
    fitted = estimate.fit(frame)
    fitted.coefficients.to_csv(estimates / "s1_coefficients.csv", index=False)
    fitted.replicates.to_csv(estimates / "s1_bootstrap_replicates.csv", index=False)
    estimate.placebo(frame).to_csv(estimates / "s1_placebo.csv", index=False)
    estimate.regime_stability(frame).to_csv(
        estimates / "s1_regime_stability.csv", index=False
    )
    typer.echo(f"estimation: n={fitted.observations}, R2={fitted.r_squared:.3f}")

    # --- portfolio state and kernels
    inputs = manuscript._kernel_inputs_from_panel(frame)
    latest = burden.dropna(subset=["debt_pct_gdp", "nominal_gdp_mio_eur"]).iloc[-1]
    debt_pct_gdp = float(latest["debt_pct_gdp"])
    nominal_gdp = float(latest["nominal_gdp_mio_eur"])
    initial_rate = float(latest["average_debt_interest_rate_pct"])

    widening = fitted.replicates["spread_widening_pp"].dropna().astype(float)
    low, high = float(widening.quantile(0.025)), float(widening.quantile(0.975))

    kernels = processed / "kernels"
    kernels.mkdir(parents=True, exist_ok=True)
    for shock in (-100, 0, 100):
        kernel.build_kernel(inputs, shock, 0.0).to_csv(
            kernels / f"kernel_shock_{shock:+d}bps.csv", index=False
        )
    bias = kernel.bias_table(
        inputs, 100, 0.0, min(0.0, low), max(0.0, high)
    )
    bias.to_csv(kernels / "kernel_bias.csv", index=False)
    kernel.fiscal_translation(bias, debt_pct_gdp, 100, nominal_gdp).to_csv(
        kernels / "kernel_bias_fiscal.csv", index=False
    )

    # --- scenarios and backtest
    scenarios = processed / "scenarios"
    scenarios.mkdir(parents=True, exist_ok=True)
    paths = simulate.simulate_paths(inputs, initial_rate, debt_pct_gdp, nominal_gdp)
    paths.to_csv(scenarios / "pass_through_paths.csv", index=False)
    simulate.half_life(paths).to_csv(scenarios / "half_life.csv", index=False)

    scores = simulate.backtest_across_cuts(
        burden,
        frame,
        lambda as_of: manuscript._kernel_inputs_from_panel(frame, as_of),
        cut_years=(2014, 2018, 2021),
    )
    scores.to_csv(scenarios / "backtest_scores.csv", index=False)
    simulate.backtest_summary(scores).to_csv(
        scenarios / "backtest_summary.csv", index=False
    )

    # --- manuscript inputs
    paper_command(config=config, paper_dir=paper_dir)
    typer.echo("repricing pipeline completed")
