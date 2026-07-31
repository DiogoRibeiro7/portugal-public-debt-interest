"""Guards for the stylised cohort refinancing model.

The model is arithmetic, so most of these are exact identities rather than
tolerance checks. The two that matter most are the zero-shock baseline (a shock
of nothing must cost nothing) and the immediate-full-refinancing case, which
must reconcile with the static full-pass-through sensitivity computed
elsewhere in the library.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pt_debt_interest.exceptions import ValidationError
from pt_debt_interest.refinancing import (
    DEFAULT_SHOCKS_BPS,
    RefinancingScenario,
    basis_points_to_rate,
    build_refinancing_assumptions,
    build_refinancing_results,
    load_refinancing_scenarios,
    static_full_pass_through_pct_gdp,
)
from pt_debt_interest.scenarios import static_rate_shock_table

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "refinancing_scenarios.yaml"
PAPER = REPO_ROOT / "paper" / "portugal_public_debt_interest_report.tex"
TABLES = REPO_ROOT / "reports" / "tables"

DEBT_PCT_GDP = 89.70
NOMINAL_GDP = 306_749.6


def _scenario(share: float, horizon: int = 10, name: str = "test") -> RefinancingScenario:
    return RefinancingScenario(
        name=name,
        annual_refinancing_share=share,
        horizon_years=horizon,
        initial_average_portfolio_rate_pct=2.1849,
        baseline_new_issuance_rate_pct=3.07583,
        debt_pct_gdp=DEBT_PCT_GDP,
        nominal_gdp_mio_eur=NOMINAL_GDP,
        paths_fixed=True,
        description="test scenario",
        implied_average_maturity_years=(1.0 / share if share > 0 else 0.0),
        source="test",
    )


def _configured() -> dict[str, RefinancingScenario]:
    if not CONFIG.is_file():
        pytest.skip("refinancing configuration is not present")
    return load_refinancing_scenarios(CONFIG)


def _paper_source() -> str:
    if not PAPER.is_file():
        pytest.skip("paper source is not present")
    return PAPER.read_text(encoding="utf-8")


def test_basis_points_conversion_exact() -> None:
    assert basis_points_to_rate(0) == 0.0
    assert basis_points_to_rate(50) == 0.005
    assert basis_points_to_rate(100) == 0.01
    assert basis_points_to_rate(200) == 0.02
    with pytest.raises(ValidationError):
        basis_points_to_rate(True)  # type: ignore[arg-type]


def test_zero_shock_incremental_cost_is_zero() -> None:
    results = build_refinancing_results(_configured(), DEFAULT_SHOCKS_BPS)
    zero = results.loc[results["shock_bps"].eq(0)]
    assert not zero.empty

    assert zero["incremental_burden_pct_gdp"].abs().max() == 0.0
    assert zero["incremental_interest_mio_eur"].abs().max() == 0.0
    assert zero["cumulative_incremental_interest_mio_eur"].abs().max() == 0.0


def test_immediate_full_refinancing_matches_static_full_pass_through() -> None:
    """A stock repriced entirely in year one must equal the static bound.

    Both sides use the year-end Maastricht debt ratio as the debt concept, so
    the comparison is like for like.
    """
    scenarios = {"immediate": _scenario(1.0, horizon=3, name="immediate")}
    results = build_refinancing_results(scenarios, (0, 100))
    shocked = results.loc[results["shock_bps"].eq(100) & results["horizon_year"].eq(1)].iloc[0]

    expected = static_full_pass_through_pct_gdp(DEBT_PCT_GDP, 100)
    assert shocked["incremental_burden_pct_gdp"] == pytest.approx(expected, abs=1e-12)

    # And it must equal what the static sensitivity table reports.
    static_row = static_rate_shock_table(DEBT_PCT_GDP, [100]).iloc[0]
    assert shocked["incremental_burden_pct_gdp"] == pytest.approx(
        float(static_row["additional_interest_pct_gdp_full_pass_through"]), abs=1e-12
    )


def test_cumulative_refinancing_is_monotonic() -> None:
    results = build_refinancing_results(_configured(), DEFAULT_SHOCKS_BPS)
    for (_, _), group in results.groupby(["scenario", "shock_bps"]):
        cumulative = group.sort_values("horizon_year")["cumulative_refinancing_share"]
        assert cumulative.is_monotonic_increasing


def test_slow_scenario_passes_through_slower_than_fast() -> None:
    scenarios = _configured()
    assert {"slow", "fast"}.issubset(scenarios.keys())
    results = build_refinancing_results(scenarios, (0, 100))
    shocked = results.loc[results["shock_bps"].eq(100)]

    slow = shocked.loc[shocked["scenario"].eq("slow")].set_index("horizon_year")
    fast = shocked.loc[shocked["scenario"].eq("fast")].set_index("horizon_year")

    for horizon_year in range(1, 6):
        assert (
            slow.loc[horizon_year, "incremental_burden_pct_gdp"]
            < fast.loc[horizon_year, "incremental_burden_pct_gdp"]
        ), f"slow should trail fast at year {horizon_year}"


def test_no_cohort_refinanced_twice() -> None:
    """Annual shares must account for the original stock exactly once."""
    for scenario in _configured().values():
        shares = scenario.annual_shares()
        assert sum(shares) <= 1.0 + 1e-12
        # Once the stock is exhausted, later years reprice nothing.
        exhausted = False
        for share in shares:
            if exhausted:
                assert share == 0.0
            if sum(shares[: shares.index(share) + 1]) >= 1.0 - 1e-12:
                exhausted = True


def test_refinancing_shares_non_negative() -> None:
    results = build_refinancing_results(_configured(), DEFAULT_SHOCKS_BPS)
    assert results["annual_refinancing_share"].min() >= 0.0
    assert results["legacy_share"].min() >= -1e-12

    with pytest.raises(ValidationError):
        _scenario(-0.1)
    with pytest.raises(ValidationError):
        _scenario(0.0)


def test_cumulative_share_not_above_one() -> None:
    results = build_refinancing_results(_configured(), DEFAULT_SHOCKS_BPS)
    assert results["cumulative_refinancing_share"].max() <= 1.0 + 1e-12

    # A share above one is rejected outright rather than clipped silently.
    with pytest.raises(ValidationError):
        _scenario(1.5)


def test_baseline_and_shock_match_before_shock() -> None:
    """At the horizon origin nothing has been repriced, so paths coincide."""
    results = build_refinancing_results(_configured(), DEFAULT_SHOCKS_BPS)
    origin = results.loc[results["horizon_year"].eq(0)]
    assert not origin.empty

    assert origin["incremental_burden_pct_gdp"].abs().max() == 0.0
    assert (
        origin["average_portfolio_rate_pct"] - origin["baseline_average_portfolio_rate_pct"]
    ).abs().max() == 0.0
    assert origin["cumulative_refinancing_share"].max() == 0.0


def test_assumptions_record_every_configured_input() -> None:
    assumptions = build_refinancing_assumptions(_configured(), DEFAULT_SHOCKS_BPS)
    required = {
        "scenario",
        "horizon_year",
        "horizon_years",
        "shock_bps",
        "annual_refinancing_share",
        "cumulative_refinancing_share",
        "initial_average_portfolio_rate_pct",
        "baseline_new_issuance_rate_pct",
        "shocked_new_issuance_rate_pct",
        "debt_pct_gdp",
        "nominal_gdp_mio_eur",
        "debt_ratio_path",
        "nominal_gdp_path",
        "source",
    }
    assert required.issubset(assumptions.columns)
    assert (assumptions["debt_ratio_path"] == "fixed").all()
    assert (assumptions["nominal_gdp_path"] == "fixed").all()


def test_main_figure_uses_incremental_burden() -> None:
    source = _paper_source()
    assert "15_refinancing_incremental_burden" in source, (
        "the report does not include the incremental-burden figure"
    )
    # The superseded total-burden figure must not be the headline any more.
    assert "09_refinancing_shock_paths" not in source


def test_report_contains_refinancing_assumptions_table() -> None:
    source = _paper_source()
    assert "refinancing_assumptions.tex" in source, (
        "the assumptions table is not included in the report"
    )
    table = TABLES / "refinancing_assumptions.tex"
    if not table.is_file():
        pytest.skip("assumptions table has not been generated")
    content = table.read_text(encoding="utf-8")
    for scenario in ("Slow", "Central", "Fast"):
        assert scenario in content
    assert "7.2" in content, "the sourced average maturity is not shown"
    assert "IGCP" in content, "the assumption source is not cited"


def test_report_labels_model_as_stylised() -> None:
    source = _paper_source()
    assert "stylised" in source.lower(), "the model is not labelled stylised"
    assert "not a forecast" in source.lower(), "the report does not disclaim forecasting"
    # The vague pointer to hidden configuration must be gone.
    stale_phrase = "configured refinancing " + "shares"
    assert stale_phrase not in source
