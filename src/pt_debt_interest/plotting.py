"""Publication-oriented charts."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .interest_decomposition import build_interest_burden_decomposition
from .panel import aggregate_flag_mask
from .scenarios import refinancing_pass_through


def _source_note(frame: pd.DataFrame) -> str:
    sources = _metadata_values(frame, "source", "processed data")
    bases = _metadata_values(frame, "accounting_basis", "not applicable")
    statuses = _metadata_values(frame, "observation_status", "not applicable")
    return f"Source: {sources}; basis: {bases}; status: {statuses}"


def _metadata_values(frame: pd.DataFrame, column: str, default: str) -> str:
    if column not in frame.columns:
        return default
    values = sorted(frame[column].dropna().astype(str).unique())
    return ", ".join(values) if values else default


def _save(fig: Figure, path: Path) -> list[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    png_path = path.with_suffix(".png")
    svg_path = path.with_suffix(".svg")
    pdf_path = path.with_suffix(".pdf")
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return [png_path, svg_path, pdf_path]


def _annotate_source(ax: Axes, frame: pd.DataFrame) -> None:
    ax.text(
        0.0,
        -0.16,
        _source_note(frame),
        transform=ax.transAxes,
        fontsize=8,
        alpha=0.75,
    )


def plot_interest_burden(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Plot interest expenditure as a percentage of GDP."""
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(frame["year"], frame["interest_pct_gdp"], marker="o", markersize=3)
    ax.set_title("Portugal: general-government interest expenditure")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percentage of GDP")
    ax.grid(True, alpha=0.25)
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "01_interest_pct_gdp")


def plot_interest_euros(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Plot nominal annual interest expenditure."""
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(frame["year"], frame["interest_mio_eur"] / 1_000.0, marker="o", markersize=3)
    ax.set_title("Portugal: annual general-government interest expenditure")
    ax.set_xlabel("Year")
    ax.set_ylabel("Billion euro")
    ax.grid(True, alpha=0.25)
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "02_interest_billion_eur")


def plot_debt_and_rate(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Plot the debt ratio and average-debt interest rate in stacked panels."""
    required = {"debt_pct_gdp", "average_debt_interest_rate_pct"}
    if not required.issubset(frame.columns):
        return []
    fig, (ax_debt, ax_rate) = plt.subplots(
        2,
        1,
        figsize=(11, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [1, 1]},
    )
    ax_debt.plot(frame["year"], frame["debt_pct_gdp"], label="Debt-to-GDP")
    ax_debt.set_title("Debt stock and effective interest cost")
    ax_debt.set_ylabel("Debt, percentage of GDP")
    ax_debt.grid(True, alpha=0.25)
    ax_debt.legend(loc="best")
    ax_rate.plot(
        frame["year"],
        frame["average_debt_interest_rate_pct"],
        linestyle="--",
        label="Average-debt rate",
    )
    ax_rate.set_xlabel("Year")
    ax_rate.set_ylabel("Average-debt interest rate, percent")
    ax_rate.grid(True, alpha=0.25)
    ax_rate.legend(loc="best")
    _annotate_source(ax_rate, frame)
    return _save(fig, output_dir / "03_debt_and_average_debt_rate")


def plot_balances(frame: pd.DataFrame, output_dir: Path) -> list[Path] | None:
    """Plot overall and primary balances when available."""
    required = {"overall_balance_pct_gdp", "primary_balance_pct_gdp"}
    if not required.issubset(frame.columns):
        return None
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axhline(0.0, linewidth=1)
    ax.plot(frame["year"], frame["overall_balance_pct_gdp"], label="Overall balance")
    ax.plot(frame["year"], frame["primary_balance_pct_gdp"], label="Primary balance")
    ax.set_title("Portugal: fiscal balance before and after interest")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percentage of GDP")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "04_overall_and_primary_balance")


def plot_government_expenditure(frame: pd.DataFrame, output_dir: Path) -> list[Path] | None:
    """Plot general-government expenditure in euros and percent of GDP."""
    required = {"government_expenditure_mio_eur", "government_expenditure_pct_gdp"}
    if not required.issubset(frame.columns):
        return None
    complete = frame.dropna(subset=list(required))
    if complete.empty:
        return None
    fig, (ax_eur, ax_ratio) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    ax_eur.plot(
        complete["year"],
        complete["government_expenditure_mio_eur"] / 1_000.0,
        label="Expenditure, EUR billion",
    )
    ax_eur.set_title("Portugal: general-government total expenditure")
    ax_eur.set_ylabel("Billion euro")
    ax_eur.grid(True, alpha=0.25)
    ax_eur.legend(loc="best")
    ax_ratio.plot(
        complete["year"],
        complete["government_expenditure_pct_gdp"],
        linestyle="--",
        label="Expenditure, % GDP",
    )
    ax_ratio.set_xlabel("Year")
    ax_ratio.set_ylabel("Percentage of GDP")
    ax_ratio.grid(True, alpha=0.25)
    ax_ratio.legend(loc="best")
    _annotate_source(ax_ratio, complete)
    return _save(fig, output_dir / "11_government_expenditure")


def plot_government_revenue(frame: pd.DataFrame, output_dir: Path) -> list[Path] | None:
    """Plot general-government revenue in euros and percent of GDP."""
    required = {"government_revenue_mio_eur", "government_revenue_pct_gdp"}
    if not required.issubset(frame.columns):
        return None
    complete = frame.dropna(subset=list(required))
    if complete.empty:
        return None
    fig, (ax_eur, ax_ratio) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    ax_eur.plot(
        complete["year"],
        complete["government_revenue_mio_eur"] / 1_000.0,
        label="Revenue, EUR billion",
    )
    ax_eur.set_title("Portugal: general-government total revenue")
    ax_eur.set_ylabel("Billion euro")
    ax_eur.grid(True, alpha=0.25)
    ax_eur.legend(loc="best")
    ax_ratio.plot(
        complete["year"],
        complete["government_revenue_pct_gdp"],
        linestyle="--",
        label="Revenue, % GDP",
    )
    ax_ratio.set_xlabel("Year")
    ax_ratio.set_ylabel("Percentage of GDP")
    ax_ratio.grid(True, alpha=0.25)
    ax_ratio.legend(loc="best")
    _annotate_source(ax_ratio, complete)
    return _save(fig, output_dir / "12_government_revenue")


def plot_yield_pass_through(frame: pd.DataFrame, output_dir: Path) -> list[Path] | None:
    """Compare market yield and whole-portfolio average-debt rate."""
    required = {"ten_year_yield_pct", "average_debt_interest_rate_pct"}
    if not required.issubset(frame.columns):
        return None
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(frame["year"], frame["ten_year_yield_pct"], label="10-year convergence yield")
    ax.plot(
        frame["year"],
        frame["average_debt_interest_rate_pct"],
        label="Average-debt rate",
    )
    ax.set_title("Market yield versus effective cost of the debt stock")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percent")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "05_market_yield_vs_average_debt_rate")


def plot_growth_decomposition(frame: pd.DataFrame, output_dir: Path) -> list[Path] | None:
    """Plot nominal, real, and GDP-deflator growth when available."""
    required = {"nominal_gdp_growth_pct", "real_gdp_growth_pct", "gdp_deflator_growth_pct"}
    if not required.issubset(frame.columns):
        return None
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axhline(0.0, linewidth=1)
    ax.plot(frame["year"], frame["nominal_gdp_growth_pct"], label="Nominal GDP")
    ax.plot(frame["year"], frame["real_gdp_growth_pct"], label="Real GDP")
    ax.plot(frame["year"], frame["gdp_deflator_growth_pct"], label="GDP deflator")
    ax.set_title("Nominal growth, real growth, and GDP-deflator growth")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percent")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "06_growth_decomposition")


def plot_debt_dynamics(frame: pd.DataFrame, output_dir: Path) -> list[Path] | None:
    """Plot debt-dynamics contribution terms when available."""
    required = {
        "interest_growth_contribution_pp",
        "primary_balance_contribution_pp",
        "stock_flow_adjustment_pp",
        "observed_debt_ratio_change_pp",
    }
    if not required.issubset(frame.columns):
        return None
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axhline(0.0, linewidth=1)
    ax.plot(
        frame["year"],
        frame["interest_growth_contribution_pp"],
        label="Interest-growth term",
    )
    ax.plot(
        frame["year"],
        frame["primary_balance_contribution_pp"],
        label="Primary balance contribution",
    )
    ax.plot(
        frame["year"],
        frame["stock_flow_adjustment_pp"],
        label="Stock-flow residual",
    )
    ax.plot(
        frame["year"],
        frame["observed_debt_ratio_change_pp"],
        linestyle="--",
        label="Observed debt-ratio change",
    )
    ax.set_title("Debt-dynamics contribution terms")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percentage of GDP")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "07_debt_dynamics")


def plot_interest_burden_decomposition(
    frame: pd.DataFrame,
    output_dir: Path,
) -> list[Path] | None:
    """Plot interval endpoint interest-burden decompositions."""
    required = {
        "rate_effect_pp",
        "debt_exposure_effect_pp",
        "total_change_pp",
        "start_year",
        "end_year",
    }
    if not required.issubset(frame.columns):
        try:
            frame = build_interest_burden_decomposition(frame)
        except Exception:
            return None
    required = {
        "rate_effect_pp",
        "debt_exposure_effect_pp",
        "total_change_pp",
        "start_year",
        "end_year",
    }
    if not required.issubset(frame.columns):
        return None
    complete = frame.dropna(subset=list(required))
    if complete.empty:
        return None
    complete = complete.sort_values(["start_year", "end_year"]).copy()
    complete["interval"] = (
        complete["start_year"].astype(int).astype(str)
        + "-"
        + complete["end_year"].astype(int).astype(str)
    )
    positions = np.arange(len(complete))
    width = 0.36
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axhline(0.0, linewidth=1)
    ax.bar(
        positions - width / 2,
        complete["rate_effect_pp"],
        width=width,
        label="Average financing-cost effect",
    )
    ax.bar(
        positions + width / 2,
        complete["debt_exposure_effect_pp"],
        width=width,
        label="Debt-exposure effect",
    )
    ax.scatter(
        positions,
        complete["total_change_pp"],
        color="#111827",
        marker="D",
        s=36,
        zorder=3,
        label="Total reconstructed change",
    )
    ax.set_title("Endpoint decomposition of the interest-burden change")
    ax.set_xlabel("Interval")
    ax.set_ylabel("Percentage points of GDP")
    ax.set_xticks(positions)
    ax.set_xticklabels(complete["interval"], rotation=30, ha="right")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _annotate_source(ax, complete)
    return _save(fig, output_dir / "10_interest_burden_decomposition")


def plot_european_comparison(
    panel_frame: pd.DataFrame | None,
    output_dir: Path,
) -> list[Path] | None:
    """Plot latest cross-country interest burdens from the comparator panel."""
    if panel_frame is None or panel_frame.empty:
        return None
    required = {"geo", "year", "interest_pct_gdp"}
    if not required.issubset(panel_frame.columns):
        return None
    panel = panel_frame.copy()
    if "observation_status" in panel.columns:
        panel = panel.loc[panel["observation_status"] == "observed"]
    if "is_aggregate" in panel.columns:
        panel = panel.loc[~aggregate_flag_mask(panel["is_aggregate"])]
    panel["year_numeric"] = pd.to_numeric(panel["year"], errors="coerce")
    panel = panel.loc[
        np.isfinite(panel["year_numeric"]) & panel["year_numeric"].mod(1).eq(0)
    ]
    panel = panel.dropna(subset=["interest_pct_gdp"])
    panel = panel.dropna(subset=["year_numeric"])
    if panel.empty:
        return None
    portugal_years = panel.loc[panel["geo"].astype(str).eq("PT"), "year_numeric"]
    if portugal_years.empty:
        return None
    latest_year = int(portugal_years.max())
    latest = panel.loc[panel["year_numeric"].eq(latest_year)].copy()
    if latest.empty:
        return None
    latest["label"] = latest.get("geo_name", latest["geo"]).fillna(latest["geo"])
    latest = latest.sort_values("interest_pct_gdp", ascending=True)
    colors = ["#2563eb" if geo == "PT" else "#6b7280" for geo in latest["geo"].astype(str)]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(latest["label"], latest["interest_pct_gdp"], color=colors)
    ax.set_title(f"European comparison of interest burden, {latest_year}")
    ax.set_xlabel("Interest expenditure, percentage of GDP")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    for index, value in enumerate(latest["interest_pct_gdp"]):
        ax.text(float(value), index, f" {float(value):.2f}", va="center", fontsize=8)
    _annotate_source(ax, latest)
    return _save(fig, output_dir / "08_european_comparison")


def refinancing_shock_paths(
    frame: pd.DataFrame,
    shocks_bps: list[int],
    refinancing_shares: list[float],
) -> pd.DataFrame:
    """Build configured refinancing-shock paths from the latest observed row."""
    if not shocks_bps or not refinancing_shares:
        return pd.DataFrame()
    baseline_columns = ["interest_pct_gdp", "debt_pct_gdp"]
    required = {*baseline_columns, "observation_status", "year"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    observed = (
        frame.loc[frame["observation_status"] == "observed"]
        .dropna(subset=baseline_columns)
        .sort_values("year")
    )
    if observed.empty:
        return pd.DataFrame()
    latest = observed.iloc[-1]
    pieces = [
        refinancing_pass_through(
            float(latest["interest_pct_gdp"]),
            float(latest["debt_pct_gdp"]),
            shock,
            refinancing_shares,
        ).assign(baseline_year=int(latest["year"]))
        for shock in shocks_bps
    ]
    return pd.concat(pieces, ignore_index=True)


def plot_refinancing_shock_paths(
    scenario_frame: pd.DataFrame | None,
    output_dir: Path,
) -> list[Path] | None:
    """Plot gradual interest-burden paths under configured refinancing shocks."""
    if scenario_frame is None or scenario_frame.empty:
        return None
    required = {"horizon_year", "shock_bps", "interest_pct_gdp_scenario"}
    if not required.issubset(scenario_frame.columns):
        return None
    fig, ax = plt.subplots(figsize=(11, 6))
    for shock, group in scenario_frame.sort_values(["shock_bps", "horizon_year"]).groupby(
        "shock_bps"
    ):
        shock_value = cast(float, shock)
        ax.plot(
            group["horizon_year"],
            group["interest_pct_gdp_scenario"],
            marker="o",
            markersize=3,
            label=f"+{shock_value:.0f} bps",
        )
    baseline_year: int | str = "latest"
    if (
        "baseline_year" in scenario_frame.columns
        and not scenario_frame["baseline_year"].dropna().empty
    ):
        baseline_year = int(cast(float, scenario_frame["baseline_year"].dropna().iloc[0]))
    ax.set_title(f"Refinancing shock paths from {baseline_year} baseline")
    ax.set_xlabel("Years after shock")
    ax.set_ylabel("Interest expenditure, percentage of GDP")
    ax.grid(True, alpha=0.25)
    ax.legend(title="Shock")
    ax.text(
        0.0,
        -0.16,
        "Source: deterministic arithmetic simulation from processed data",
        transform=ax.transAxes,
        fontsize=8,
        alpha=0.75,
    )
    return _save(fig, output_dir / "09_refinancing_shock_paths")


def write_refinancing_scenarios(
    scenario_frame: pd.DataFrame,
    output_dir: Path,
) -> Path | None:
    """Write the scenario table used by the refinancing figure."""
    if scenario_frame.empty:
        return None
    reports_dir = output_dir.parent
    reports_dir.mkdir(parents=True, exist_ok=True)
    destination = reports_dir / "refinancing_scenarios.csv"
    scenario_frame.to_csv(destination, index=False)
    return destination


def _write_manifest(paths: list[Path], frame: pd.DataFrame, output_dir: Path) -> Path:
    manifest = pd.DataFrame(
        {
            "filename": [path.name for path in paths],
            "source_note": [_source_note(frame)] * len(paths),
        }
    )
    manifest_path = output_dir / "figures_manifest.csv"
    manifest.to_csv(manifest_path, index=False)
    return manifest_path


def generate_all_plots(
    frame: pd.DataFrame,
    output_dir: Path,
    panel_frame: pd.DataFrame | None = None,
    shocks_bps: list[int] | None = None,
    refinancing_shares: list[float] | None = None,
) -> list[Path]:
    """Generate all available charts."""
    scenario_frame = refinancing_shock_paths(
        frame,
        shocks_bps or [],
        refinancing_shares or [],
    )
    candidates = [
        plot_interest_burden(frame, output_dir),
        plot_interest_euros(frame, output_dir),
        plot_debt_and_rate(frame, output_dir),
        plot_balances(frame, output_dir),
        plot_yield_pass_through(frame, output_dir),
        plot_growth_decomposition(frame, output_dir),
        plot_debt_dynamics(frame, output_dir),
        plot_european_comparison(panel_frame, output_dir),
        plot_refinancing_shock_paths(scenario_frame, output_dir),
        plot_interest_burden_decomposition(frame, output_dir),
        plot_government_expenditure(frame, output_dir),
        plot_government_revenue(frame, output_dir),
    ]
    paths = [path for group in candidates if group is not None for path in group]
    scenario_path = write_refinancing_scenarios(scenario_frame, output_dir)
    if scenario_path is not None:
        paths.append(scenario_path)
    paths.append(_write_manifest(paths, frame, output_dir))
    return paths
