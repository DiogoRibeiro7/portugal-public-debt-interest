"""Publication-oriented charts."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

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
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return [png_path, svg_path]


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
    """Plot the debt ratio and implicit interest rate on separate axes."""
    fig, ax_left = plt.subplots(figsize=(11, 6))
    ax_right = ax_left.twinx()
    ax_left.plot(frame["year"], frame["debt_pct_gdp"], label="Debt-to-GDP")
    ax_right.plot(
        frame["year"],
        frame["implicit_interest_rate_pct"],
        linestyle="--",
        label="Implicit interest rate",
    )
    ax_left.set_title("Debt stock and effective interest cost")
    ax_left.set_xlabel("Year")
    ax_left.set_ylabel("Debt, percentage of GDP")
    ax_right.set_ylabel("Implicit interest rate, percent")
    ax_left.grid(True, alpha=0.25)
    lines = [*ax_left.get_lines(), *ax_right.get_lines()]
    ax_left.legend(lines, [str(line.get_label()) for line in lines], loc="best")
    _annotate_source(ax_left, frame)
    return _save(fig, output_dir / "03_debt_and_implicit_rate")


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


def plot_yield_pass_through(frame: pd.DataFrame, output_dir: Path) -> list[Path] | None:
    """Compare market yield and whole-portfolio implicit interest rate."""
    if "ten_year_yield_pct" not in frame.columns:
        return None
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(frame["year"], frame["ten_year_yield_pct"], label="10-year convergence yield")
    ax.plot(
        frame["year"],
        frame["implicit_interest_rate_pct"],
        label="Implicit interest rate",
    )
    ax.set_title("Market yield versus effective cost of the debt stock")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percent")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "05_market_yield_vs_implicit_rate")


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
        "debt_stabilising_primary_balance_pct_gdp",
        "primary_balance_pct_gdp",
        "stock_flow_adjustment_pct_gdp",
    }
    if not required.issubset(frame.columns):
        return None
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.axhline(0.0, linewidth=1)
    ax.plot(
        frame["year"],
        frame["debt_stabilising_primary_balance_pct_gdp"],
        label="Interest-growth term",
    )
    ax.plot(frame["year"], frame["primary_balance_pct_gdp"], label="Primary balance")
    ax.plot(
        frame["year"],
        frame["stock_flow_adjustment_pct_gdp"],
        label="Stock-flow residual",
    )
    ax.set_title("Debt-dynamics contribution terms")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percentage of GDP")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _annotate_source(ax, frame)
    return _save(fig, output_dir / "07_debt_dynamics")


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
        panel = panel.loc[~panel["is_aggregate"].fillna(False).astype(bool)]
    panel = panel.dropna(subset=["interest_pct_gdp"])
    if panel.empty:
        return None
    latest_year = int(panel["year"].max())
    latest = panel.loc[panel["year"].eq(latest_year)].copy()
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
    required = {"interest_pct_gdp", "debt_pct_gdp", "observation_status", "year"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    observed = frame.loc[frame["observation_status"] == "observed"].sort_values("year")
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
    ]
    paths = [path for group in candidates if group is not None for path in group]
    paths.append(_write_manifest(paths, frame, output_dir))
    return paths
