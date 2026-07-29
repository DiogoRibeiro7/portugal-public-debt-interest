from pathlib import Path

import pandas as pd
import pytest

from pt_debt_interest.plotting import (
    generate_all_plots,
    plot_debt_dynamics,
    plot_yield_pass_through,
    refinancing_shock_paths,
)
from pt_debt_interest.reporting import generate_report


def _fixture_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2021, 2022, 2023],
            "interest_mio_eur": [5000.0, 4800.0, 5500.0],
            "interest_pct_gdp": [2.2, 2.0, 2.1],
            "government_expenditure_mio_eur": [105000.0, 110000.0, 112000.0],
            "government_expenditure_pct_gdp": [47.7, 44.9, 42.3],
            "government_revenue_mio_eur": [101000.0, 109000.0, 114000.0],
            "government_revenue_pct_gdp": [45.9, 44.5, 43.0],
            "debt_pct_gdp": [125.0, 115.0, 105.0],
            "average_debt_interest_rate_pct": [2.0, 1.8, 2.1],
            "overall_balance_pct_gdp": [-2.0, -0.3, 1.0],
            "primary_balance_pct_gdp": [0.2, 1.7, 3.1],
            "ten_year_yield_pct": [0.3, 1.7, 3.0],
            "nominal_gdp_growth_pct": [None, 11.0, 8.0],
            "real_gdp_growth_pct": [5.6, 6.8, 2.5],
            "gdp_deflator_growth_pct": [None, 3.9, 5.4],
            "interest_growth_contribution_pp": [None, -9.0, -6.0],
            "primary_balance_contribution_pp": [None, -1.7, -3.1],
            "stock_flow_adjustment_pp": [None, -1.0, 0.5],
            "observed_debt_ratio_change_pp": [None, -10.0, -10.0],
            "rate_effect_pp": [None, 0.1, 0.2],
            "average_debt_ratio_effect_pp": [None, -0.2, 0.1],
            "interaction_effect_pp": [None, 0.0, 0.0],
            "calculated_interest_burden_change_pp": [None, -0.1, 0.3],
            "source": ["Eurostat", "Eurostat", "Eurostat"],
            "accounting_basis": ["ESA2010", "ESA2010", "ESA2010"],
            "observation_status": ["observed", "observed", "observed"],
        }
    )


def _panel_fixture_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "geo": ["PT", "ES", "IT", "EA20"],
            "geo_name": ["Portugal", "Spain", "Italy", "Euro area"],
            "year": [2023, 2023, 2023, 2023],
            "interest_pct_gdp": [2.1, 2.4, 3.6, 2.0],
            "source": ["Eurostat"] * 4,
            "accounting_basis": ["ESA2010"] * 4,
            "observation_status": ["observed"] * 4,
            "is_aggregate": [False, False, False, True],
        }
    )


def _panel_with_string_aggregate_flags() -> pd.DataFrame:
    frame = _panel_fixture_frame()
    frame["is_aggregate"] = ["False", "false", "FALSE", "True"]
    return frame


def _panel_with_newer_non_portugal_year() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "geo": ["PT", "ES", "IT", "ES"],
            "geo_name": ["Portugal", "Spain", "Italy", "Spain"],
            "year": [2023, 2023, 2023, 2024],
            "interest_pct_gdp": [2.1, 2.4, 3.6, 2.5],
            "source": ["Eurostat"] * 4,
            "accounting_basis": ["ESA2010"] * 4,
            "observation_status": ["observed"] * 4,
            "is_aggregate": [False] * 4,
        }
    )


def _panel_with_malformed_portugal_year() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "geo": ["PT", "ES"],
            "geo_name": ["Portugal", "Spain"],
            "year": ["not-a-year", 2023],
            "interest_pct_gdp": [2.1, 2.4],
            "source": ["Eurostat"] * 2,
            "accounting_basis": ["ESA2010"] * 2,
            "observation_status": ["observed"] * 2,
            "is_aggregate": [False] * 2,
        }
    )


def _panel_with_fractional_portugal_year() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "geo": ["PT", "ES"],
            "geo_name": ["Portugal", "Spain"],
            "year": [2023.5, 2023.5],
            "interest_pct_gdp": [2.1, 2.4],
            "source": ["Eurostat"] * 2,
            "accounting_basis": ["ESA2010"] * 2,
            "observation_status": ["observed"] * 2,
            "is_aggregate": [False] * 2,
        }
    )


def test_generate_all_plots_writes_png_svg_pdf_and_manifest(tmp_path: Path) -> None:
    paths = generate_all_plots(
        _fixture_frame(),
        tmp_path,
        panel_frame=_panel_fixture_frame(),
        shocks_bps=[100, 200],
        refinancing_shares=[0.25, 0.25],
    )
    names = {path.name for path in paths}

    assert "01_interest_pct_gdp.png" in names
    assert "01_interest_pct_gdp.svg" in names
    assert "01_interest_pct_gdp.pdf" in names
    assert "08_european_comparison.png" in names
    assert "09_refinancing_shock_paths.svg" in names
    assert "09_refinancing_shock_paths.pdf" in names
    assert "10_interest_burden_decomposition.png" in names
    assert "11_government_expenditure.svg" in names
    assert "11_government_expenditure.pdf" in names
    assert "12_government_revenue.svg" in names
    assert "12_government_revenue.pdf" in names
    assert "refinancing_scenarios.csv" in names
    assert "figures_manifest.csv" in names


def test_debt_dynamics_plot_does_not_receive_average_debt_rate(tmp_path: Path) -> None:
    frame = _fixture_frame().drop(columns=["average_debt_interest_rate_pct"])

    paths = plot_debt_dynamics(frame, tmp_path)

    assert paths is not None
    assert {path.name for path in paths} == {
        "07_debt_dynamics.png",
        "07_debt_dynamics.svg",
        "07_debt_dynamics.pdf",
    }


def test_market_yield_comparison_receives_average_debt_rate(tmp_path: Path) -> None:
    paths = plot_yield_pass_through(_fixture_frame(), tmp_path)

    assert paths is not None
    assert "05_market_yield_vs_average_debt_rate.png" in {path.name for path in paths}


def test_market_yield_comparison_rejects_missing_average_debt_rate(tmp_path: Path) -> None:
    frame = _fixture_frame().drop(columns=["average_debt_interest_rate_pct"])

    assert plot_yield_pass_through(frame, tmp_path) is None


def test_generate_all_plots_parses_string_aggregate_flags(tmp_path: Path) -> None:
    paths = generate_all_plots(
        _fixture_frame(),
        tmp_path,
        panel_frame=_panel_with_string_aggregate_flags(),
    )
    names = {path.name for path in paths}

    assert "08_european_comparison.png" in names


def test_generate_all_plots_uses_latest_panel_year_with_portugal(tmp_path: Path) -> None:
    paths = generate_all_plots(
        _fixture_frame(),
        tmp_path,
        panel_frame=_panel_with_newer_non_portugal_year(),
    )
    names = {path.name for path in paths}

    assert "08_european_comparison.png" in names


def test_generate_all_plots_skips_malformed_panel_year(tmp_path: Path) -> None:
    paths = generate_all_plots(
        _fixture_frame(),
        tmp_path,
        panel_frame=_panel_with_malformed_portugal_year(),
    )
    names = {path.name for path in paths}

    assert "08_european_comparison.png" not in names


def test_generate_all_plots_skips_fractional_panel_year(tmp_path: Path) -> None:
    paths = generate_all_plots(
        _fixture_frame(),
        tmp_path,
        panel_frame=_panel_with_fractional_portugal_year(),
    )
    names = {path.name for path in paths}

    assert "08_european_comparison.png" not in names


def test_refinancing_shock_paths_uses_latest_complete_observed_row() -> None:
    frame = _fixture_frame()
    frame.loc[frame["year"] == 2023, "debt_pct_gdp"] = pd.NA

    result = refinancing_shock_paths(frame, [100], [0.25])

    assert result.loc[0, "baseline_year"] == 2022
    assert result.loc[0, "interest_pct_gdp_scenario"] > 2.0


def test_refinancing_shock_paths_skips_incomplete_baseline() -> None:
    frame = _fixture_frame()
    frame["debt_pct_gdp"] = pd.NA

    result = refinancing_shock_paths(frame, [100], [0.25])

    assert result.empty


def test_generate_report_writes_generated_values(tmp_path: Path) -> None:
    figure = tmp_path / "01_interest_pct_gdp.png"
    figure.write_text("placeholder", encoding="utf-8")
    destination = generate_report(
        _fixture_frame(),
        tmp_path / "summary.md",
        1995,
        [100],
        panel_frame=_panel_fixture_frame(),
        figure_paths=[figure],
    )
    content = destination.read_text(encoding="utf-8")

    assert "2023" in content
    assert "5.5 billion" in content
    assert "Total general-government expenditure" in content
    assert "Total general-government revenue" in content
    assert "European comparison" in content
    assert "Portugal ranked" in content
    assert "Static full-pass-through sensitivities" in content
    assert "01_interest_pct_gdp.png" in content


def test_generate_report_parses_string_aggregate_flags(tmp_path: Path) -> None:
    destination = generate_report(
        _fixture_frame(),
        tmp_path / "summary.md",
        1995,
        [100],
        panel_frame=_panel_with_string_aggregate_flags(),
    )
    content = destination.read_text(encoding="utf-8")

    assert "Portugal ranked" in content
    assert "**3** non-aggregate comparator countries" in content


def test_generate_report_uses_latest_panel_year_with_portugal(tmp_path: Path) -> None:
    destination = generate_report(
        _fixture_frame(),
        tmp_path / "summary.md",
        1995,
        [100],
        panel_frame=_panel_with_newer_non_portugal_year(),
    )
    content = destination.read_text(encoding="utf-8")

    assert "In **2023**" in content
    assert "Portugal ranked" in content


def test_generate_report_skips_malformed_panel_year(tmp_path: Path) -> None:
    destination = generate_report(
        _fixture_frame(),
        tmp_path / "summary.md",
        1995,
        [100],
        panel_frame=_panel_with_malformed_portugal_year(),
    )
    content = destination.read_text(encoding="utf-8")

    assert "Comparator-panel metrics were not available" in content


def test_generate_report_skips_fractional_panel_year(tmp_path: Path) -> None:
    destination = generate_report(
        _fixture_frame(),
        tmp_path / "summary.md",
        1995,
        [100],
        panel_frame=_panel_with_fractional_portugal_year(),
    )
    content = destination.read_text(encoding="utf-8")

    assert "Comparator-panel metrics were not available" in content


def test_generate_report_rejects_missing_required_columns(tmp_path: Path) -> None:
    frame = _fixture_frame().drop(columns=["average_debt_interest_rate_pct"])

    with pytest.raises(ValueError, match="missing required columns"):
        generate_report(frame, tmp_path / "summary.md", 1995, [100])


def test_generate_report_rejects_incomplete_headline_rows(tmp_path: Path) -> None:
    frame = _fixture_frame()
    frame["average_debt_interest_rate_pct"] = pd.NA

    with pytest.raises(ValueError, match="complete headline metrics"):
        generate_report(frame, tmp_path / "summary.md", 1995, [100])


def test_generate_report_rejects_non_numeric_headline_values(tmp_path: Path) -> None:
    frame = _fixture_frame()
    frame.loc[frame["year"] == 2023, "interest_pct_gdp"] = "not-a-number"

    with pytest.raises(ValueError, match="interest_pct_gdp must be numeric"):
        generate_report(frame, tmp_path / "summary.md", 1995, [100])


def test_generate_report_rejects_non_finite_headline_values(tmp_path: Path) -> None:
    frame = _fixture_frame()
    frame.loc[frame["year"] == 2023, "debt_pct_gdp"] = float("inf")

    with pytest.raises(ValueError, match="debt_pct_gdp must be numeric"):
        generate_report(frame, tmp_path / "summary.md", 1995, [100])
