"""Stylised cohort model of refinancing pass-through.

The model is deliberately simple and fully specified in configuration. A
sovereign does not reprice its whole debt stock when yields move: only the part
that matures and is rolled over is repriced. This module tracks that
explicitly.

Mechanics
---------
At year zero the whole initial stock sits in a *legacy* cohort carrying the
initial average portfolio rate. In year ``t`` a configured share of the
**original** stock leaves the legacy cohort and enters a *refinanced* cohort at
that year's new-issuance rate. Cohorts already refinanced keep the rate they
were assigned, so no cohort is ever repriced twice. Shares are expressed
against the original stock, so the cumulative share can never exceed one.

What the model is not
---------------------
It is not a forecast, and the shares are not IGCP's redemption schedule. The
debt ratio and nominal GDP are held fixed so that the pass-through arithmetic
is visible on its own; every assumption is written to
``refinancing_assumptions.csv`` beside the results.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Final

import pandas as pd
import yaml

from .exceptions import ValidationError

#: Basis points in one unit of rate. A shock of 100 bps is exactly 0.01.
BASIS_POINTS_PER_UNIT: Final[int] = 10_000

DEFAULT_SHOCKS_BPS: Final[tuple[int, ...]] = (0, 50, 100, 200)


def basis_points_to_rate(shock_bps: int) -> float:
    """Convert basis points to a decimal rate exactly."""
    if isinstance(shock_bps, bool) or not isinstance(shock_bps, int):
        raise ValidationError("shock must be an integer number of basis points")
    return shock_bps / BASIS_POINTS_PER_UNIT


class RefinancingScenario:
    """One configured repricing profile."""

    def __init__(
        self,
        name: str,
        annual_refinancing_share: float,
        horizon_years: int,
        initial_average_portfolio_rate_pct: float,
        baseline_new_issuance_rate_pct: float,
        debt_pct_gdp: float,
        nominal_gdp_mio_eur: float,
        paths_fixed: bool,
        description: str,
        implied_average_maturity_years: float,
        source: str,
    ) -> None:
        self.name = name
        self.annual_refinancing_share = annual_refinancing_share
        self.horizon_years = horizon_years
        self.initial_average_portfolio_rate_pct = initial_average_portfolio_rate_pct
        self.baseline_new_issuance_rate_pct = baseline_new_issuance_rate_pct
        self.debt_pct_gdp = debt_pct_gdp
        self.nominal_gdp_mio_eur = nominal_gdp_mio_eur
        self.paths_fixed = paths_fixed
        self.description = description
        self.implied_average_maturity_years = implied_average_maturity_years
        self.source = source
        self._validate()

    def _validate(self) -> None:
        share = self.annual_refinancing_share
        if not math.isfinite(share) or share <= 0.0 or share > 1.0:
            raise ValidationError(f"{self.name}: annual refinancing share must lie in (0, 1]")
        if self.horizon_years <= 0:
            raise ValidationError(f"{self.name}: horizon must be positive")
        for label, value in (
            ("debt ratio", self.debt_pct_gdp),
            ("nominal GDP", self.nominal_gdp_mio_eur),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValidationError(f"{self.name}: {label} must be positive")

    def annual_shares(self) -> list[float]:
        """Share of the *original* stock repriced in each horizon year.

        The final cohort is truncated so that the cumulative share never
        exceeds the outstanding stock: once everything has been repriced, later
        years reprice nothing.
        """
        shares: list[float] = []
        remaining = 1.0
        for _ in range(self.horizon_years):
            step = min(self.annual_refinancing_share, remaining)
            shares.append(step)
            remaining -= step
        return shares


def load_refinancing_scenarios(path: Path) -> dict[str, RefinancingScenario]:
    """Load the configured scenarios."""
    if not path.is_file():
        raise ValidationError(f"refinancing scenario configuration is missing: {path}")
    with path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    defaults = raw.get("defaults", {})
    scenarios_section = raw.get("scenarios", {})
    if not scenarios_section:
        raise ValidationError("refinancing configuration defines no scenarios")

    scenarios: dict[str, RefinancingScenario] = {}
    for name, entry in scenarios_section.items():
        merged = {**defaults, **entry}
        try:
            scenarios[name] = RefinancingScenario(
                name=name,
                annual_refinancing_share=float(merged["annual_refinancing_share"]),
                horizon_years=int(merged["horizon_years"]),
                initial_average_portfolio_rate_pct=float(
                    merged["initial_average_portfolio_rate_pct"]
                ),
                baseline_new_issuance_rate_pct=float(merged["baseline_new_issuance_rate_pct"]),
                debt_pct_gdp=float(merged["debt_pct_gdp"]),
                nominal_gdp_mio_eur=float(merged["nominal_gdp_mio_eur"]),
                paths_fixed=bool(merged.get("paths_fixed", True)),
                description=str(merged.get("description", "")),
                implied_average_maturity_years=float(
                    merged.get("implied_average_maturity_years", 0.0)
                ),
                source=str(merged.get("source", "")),
            )
        except KeyError as exc:
            raise ValidationError(f"refinancing scenario {name} is missing key {exc}") from exc
    return scenarios


def build_refinancing_assumptions(
    scenarios: dict[str, RefinancingScenario],
    shocks_bps: tuple[int, ...] = DEFAULT_SHOCKS_BPS,
) -> pd.DataFrame:
    """Tabulate every assumption behind the simulation, per scenario-year."""
    rows: list[dict[str, object]] = []
    for scenario in scenarios.values():
        shares = scenario.annual_shares()
        cumulative = 0.0
        for horizon_year, share in enumerate(shares, start=1):
            cumulative += share
            for shock_bps in shocks_bps:
                shock_rate_pct = basis_points_to_rate(shock_bps) * 100.0
                rows.append(
                    {
                        "scenario": scenario.name,
                        "description": scenario.description,
                        "horizon_year": horizon_year,
                        "horizon_years": scenario.horizon_years,
                        "shock_bps": shock_bps,
                        "annual_refinancing_share": share,
                        "cumulative_refinancing_share": cumulative,
                        "implied_average_maturity_years": (scenario.implied_average_maturity_years),
                        "initial_average_portfolio_rate_pct": (
                            scenario.initial_average_portfolio_rate_pct
                        ),
                        "baseline_new_issuance_rate_pct": (scenario.baseline_new_issuance_rate_pct),
                        "shocked_new_issuance_rate_pct": (
                            scenario.baseline_new_issuance_rate_pct + shock_rate_pct
                        ),
                        "debt_pct_gdp": scenario.debt_pct_gdp,
                        "nominal_gdp_mio_eur": scenario.nominal_gdp_mio_eur,
                        "paths_fixed": scenario.paths_fixed,
                        "debt_ratio_path": "fixed" if scenario.paths_fixed else "changing",
                        "nominal_gdp_path": "fixed" if scenario.paths_fixed else "changing",
                        "source": scenario.source,
                        "interpretation": "stylised cohort model, not a forecast",
                    }
                )
    return pd.DataFrame(rows)


def _simulate_one(
    scenario: RefinancingScenario,
    shock_bps: int,
) -> pd.DataFrame:
    """Run the cohort recurrence for one scenario and one shock."""
    shock_rate_pct = basis_points_to_rate(shock_bps) * 100.0
    initial_rate = scenario.initial_average_portfolio_rate_pct
    baseline_issuance = scenario.baseline_new_issuance_rate_pct
    shocked_issuance = baseline_issuance + shock_rate_pct
    debt_stock_mio_eur = scenario.nominal_gdp_mio_eur * scenario.debt_pct_gdp / 100.0

    rows: list[dict[str, object]] = [
        {
            "scenario": scenario.name,
            "shock_bps": shock_bps,
            "horizon_year": 0,
            "annual_refinancing_share": 0.0,
            "cumulative_refinancing_share": 0.0,
            "legacy_share": 1.0,
            "average_portfolio_rate_pct": initial_rate,
            "baseline_average_portfolio_rate_pct": initial_rate,
            "interest_burden_pct_gdp": initial_rate * scenario.debt_pct_gdp / 100.0,
            "baseline_interest_burden_pct_gdp": (initial_rate * scenario.debt_pct_gdp / 100.0),
        }
    ]

    cumulative = 0.0
    # Weighted rate carried by cohorts already repriced, for each of the two
    # rate paths. A repriced cohort keeps its rate for the rest of the horizon.
    repriced_weighted_shocked = 0.0
    repriced_weighted_baseline = 0.0

    for horizon_year, share in enumerate(scenario.annual_shares(), start=1):
        cumulative += share
        repriced_weighted_shocked += share * shocked_issuance
        repriced_weighted_baseline += share * baseline_issuance
        legacy_share = 1.0 - cumulative

        rate = legacy_share * initial_rate + repriced_weighted_shocked
        baseline_rate = legacy_share * initial_rate + repriced_weighted_baseline

        rows.append(
            {
                "scenario": scenario.name,
                "shock_bps": shock_bps,
                "horizon_year": horizon_year,
                "annual_refinancing_share": share,
                "cumulative_refinancing_share": cumulative,
                "legacy_share": legacy_share,
                "average_portfolio_rate_pct": rate,
                "baseline_average_portfolio_rate_pct": baseline_rate,
                "interest_burden_pct_gdp": rate * scenario.debt_pct_gdp / 100.0,
                "baseline_interest_burden_pct_gdp": (baseline_rate * scenario.debt_pct_gdp / 100.0),
            }
        )

    frame = pd.DataFrame(rows)
    frame["incremental_burden_pct_gdp"] = (
        frame["interest_burden_pct_gdp"] - frame["baseline_interest_burden_pct_gdp"]
    )
    frame["interest_mio_eur"] = frame["average_portfolio_rate_pct"] / 100.0 * debt_stock_mio_eur
    frame["baseline_interest_mio_eur"] = (
        frame["baseline_average_portfolio_rate_pct"] / 100.0 * debt_stock_mio_eur
    )
    frame["incremental_interest_mio_eur"] = (
        frame["interest_mio_eur"] - frame["baseline_interest_mio_eur"]
    )
    frame["cumulative_incremental_interest_mio_eur"] = frame[
        "incremental_interest_mio_eur"
    ].cumsum()
    frame["debt_pct_gdp"] = scenario.debt_pct_gdp
    frame["nominal_gdp_mio_eur"] = scenario.nominal_gdp_mio_eur
    frame["debt_stock_mio_eur"] = debt_stock_mio_eur
    frame["interpretation"] = "stylised cohort model, not a forecast"
    return frame


def build_refinancing_results(
    scenarios: dict[str, RefinancingScenario],
    shocks_bps: tuple[int, ...] = DEFAULT_SHOCKS_BPS,
) -> pd.DataFrame:
    """Simulate every scenario against every shock, including the zero shock."""
    if 0 not in shocks_bps:
        raise ValidationError("a zero-shock baseline is required")
    pieces = [
        _simulate_one(scenario, shock_bps)
        for scenario in scenarios.values()
        for shock_bps in shocks_bps
    ]
    return pd.concat(pieces, ignore_index=True)


def static_full_pass_through_pct_gdp(debt_pct_gdp: float, shock_bps: int) -> float:
    """Long-run bound: the whole stock repriced at the shocked rate.

    The debt concept is the **year-end Maastricht debt ratio**, matching
    ``scenarios.static_rate_shock_table``, so the immediate-full-refinancing
    consistency check compares like with like.
    """
    return debt_pct_gdp * basis_points_to_rate(shock_bps)
