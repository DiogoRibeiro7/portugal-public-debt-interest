"""Publication-oriented charts."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_interest_burden(frame: pd.DataFrame, output_dir: Path) -> Path:
    """Plot interest expenditure as a percentage of GDP."""
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(frame["year"], frame["interest_pct_gdp"], marker="o", markersize=3)
    ax.set_title("Portugal: general-government interest expenditure")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percentage of GDP")
    ax.grid(True, alpha=0.25)
    return _save(fig, output_dir / "01_interest_pct_gdp.png")


def plot_interest_euros(frame: pd.DataFrame, output_dir: Path) -> Path:
    """Plot nominal annual interest expenditure."""
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(frame["year"], frame["interest_mio_eur"] / 1_000.0, marker="o", markersize=3)
    ax.set_title("Portugal: annual general-government interest expenditure")
    ax.set_xlabel("Year")
    ax.set_ylabel("Billion euro")
    ax.grid(True, alpha=0.25)
    return _save(fig, output_dir / "02_interest_billion_eur.png")


def plot_debt_and_rate(frame: pd.DataFrame, output_dir: Path) -> Path:
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
    lines = ax_left.get_lines() + ax_right.get_lines()
    ax_left.legend(lines, [line.get_label() for line in lines], loc="best")
    return _save(fig, output_dir / "03_debt_and_implicit_rate.png")


def plot_balances(frame: pd.DataFrame, output_dir: Path) -> Path | None:
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
    return _save(fig, output_dir / "04_overall_and_primary_balance.png")


def plot_yield_pass_through(frame: pd.DataFrame, output_dir: Path) -> Path | None:
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
    return _save(fig, output_dir / "05_market_yield_vs_implicit_rate.png")


def generate_all_plots(frame: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Generate all available charts."""
    candidates = [
        plot_interest_burden(frame, output_dir),
        plot_interest_euros(frame, output_dir),
        plot_debt_and_rate(frame, output_dir),
        plot_balances(frame, output_dir),
        plot_yield_pass_through(frame, output_dir),
    ]
    return [path for path in candidates if path is not None]
